"""Shared helpers for fable-mode guard hooks.

Design invariants (keep these true, they are the safety contract):
- FAIL-OPEN: any unexpected error must let the session proceed (exit 0). A bug
  in a guard must never brick the user's Claude Code session.
- OPT-IN: a guard only does anything when the project has opted into fable-mode
  enforcement by having a `.fable/` directory somewhere from cwd up to the root.
  No `.fable/` dir  ->  guards are inert.
"""
import json
import os
import re
import sys
import tempfile
import time


def read_hook_input():
    """Parse the hook JSON delivered on stdin. Returns {} on any problem."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except Exception:
        return {}


def start_dir(data):
    """Best-effort project dir: hook 'cwd' field, else process cwd."""
    cwd = data.get("cwd")
    if cwd and os.path.isdir(cwd):
        return cwd
    try:
        return os.getcwd()
    except Exception:
        return "."


def find_fable_dir(start):
    """Walk up from `start` looking for a `.fable/` directory.

    Stops at the filesystem root or at a git repo root (whichever comes first),
    so a stray `.fable` far up the tree can't accidentally arm every project.
    Returns the absolute path to the `.fable` dir, or None.
    """
    try:
        cur = os.path.abspath(start)
    except Exception:
        return None
    while True:
        cand = os.path.join(cur, ".fable")
        if os.path.isdir(cand):
            return cand
        # git root is a natural project boundary; don't cross it.
        if os.path.isdir(os.path.join(cur, ".git")):
            return None
        parent = os.path.dirname(cur)
        if parent == cur:  # filesystem root
            return None
        cur = parent


def ledger_path(fable_dir):
    return os.path.join(fable_dir, "LEDGER.md")


# --- model-tier ranking & per-session model cache (for the model ceiling) ---

TIER_ORDER = ("haiku", "sonnet", "opus", "fable")


def model_tier(model_str):
    """Rank a model string by capability keyword; None if unrecognized."""
    s = (model_str or "").lower()
    tiers = [i for i, k in enumerate(TIER_ORDER) if k in s]
    return max(tiers) if tiers else None


def _sessions_dir():
    d = os.path.join(tempfile.gettempdir(), "fable-mode-sessions")
    os.makedirs(d, exist_ok=True)
    return d


def _safe_sid(session_id):
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(session_id))[:120]


def save_session_model(session_id, model):
    """Cache the session's model at SessionStart so PreToolUse guards (which
    never receive `model`) can enforce the ceiling. Best-effort, fail-open."""
    if not session_id or not model:
        return
    try:
        d = _sessions_dir()
        now = time.time()
        for f in os.listdir(d):  # opportunistic self-cleanup, no SessionEnd hook needed
            p = os.path.join(d, f)
            try:
                if now - os.path.getmtime(p) > 7 * 86400:
                    os.remove(p)
            except OSError:
                pass
        with open(os.path.join(d, _safe_sid(session_id) + ".txt"), "w",
                  encoding="utf-8") as fh:
            fh.write(str(model))
    except Exception:
        pass


def load_session_model(session_id):
    if not session_id:
        return None
    try:
        with open(os.path.join(_sessions_dir(), _safe_sid(session_id) + ".txt"),
                  encoding="utf-8") as fh:
            return fh.read().strip() or None
    except Exception:
        return None


# --- evidence-on-close convention (lever 4: report evidence, not adjectives) ---

EVIDENCE_RE = re.compile(r"(evidence|verified|证据|凭证|验证)\s*[:：]", re.IGNORECASE)


# --- cross-session lessons memory (the Fable 5 "memory system") ---

def lessons_path():
    """Global lessons file, outside any project so it survives re-clones."""
    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(cfg, "fable-lessons.md")


def read_lessons(max_items=5, max_chars=600):
    """Top bullet lines from the lessons file, newest-first by convention.

    Bounded on both count and total size so the injection tax stays small.
    Returns [] on any problem (fail-open).
    """
    try:
        with open(lessons_path(), encoding="utf-8", errors="replace") as fh:
            items = [ln.strip() for ln in fh
                     if ln.strip().startswith(("-", "*"))]
    except Exception:
        return []
    out, total = [], 0
    for it in items[:max_items]:
        it = it[:200]
        if total + len(it) > max_chars:
            break
        out.append(it)
        total += len(it)
    return out


MIN_EVIDENCE_CHARS = 6


def closed_without_evidence(path):
    """List `- [x]` ledger lines whose evidence marker is missing OR hollow.

    Convention: a card may only be checked `- [x]` together with a substantive
    evidence note (`-- evidence: <command output / screenshot / test count>`).
    A marker followed by fewer than MIN_EVIDENCE_CHARS characters ("evidence:
    ok") is treated as missing — adjectives are not evidence.
    Returns [] on any read problem (fail-open).
    """
    bad = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if s[:5].lower() != "- [x]":
                    continue
                m = EVIDENCE_RE.search(s)
                if not m or len(s[m.end():].strip()) < MIN_EVIDENCE_CHARS:
                    bad.append(s)
    except Exception:
        return []
    return bad


# --- consecutive-failure streak (attribution-ladder reminder) ---

def _streak_file(session_id):
    return os.path.join(_sessions_dir(), _safe_sid(session_id) + ".fails")


def load_fail_streak(session_id):
    if not session_id:
        return 0
    try:
        with open(_streak_file(session_id), encoding="utf-8") as fh:
            return max(0, int(fh.read().strip() or 0))
    except Exception:
        return 0


def save_fail_streak(session_id, n):
    if not session_id:
        return
    try:
        with open(_streak_file(session_id), "w", encoding="utf-8") as fh:
            fh.write(str(int(n)))
    except Exception:
        pass


def parse_ledger(path):
    """Return (open_items, has_any, paused) for a ledger file.

    A ledger line is a markdown checkbox: `- [ ] ...`, `- [x] ...`, `- [~] ...`
    (case-insensitive on x). `open_items` is the list of `- [ ]` line texts.
    `has_any` is True if the file has at least one checkbox line at all.
    `paused` is True if any line starts with `PAUSED` (case-insensitive) AND
    carries a reason (>=3 chars after the marker) — the user-facing switch to
    suspend enforcement mid-round for unrelated work. A bare `PAUSED` with no
    reason is ignored: pausing must be attributable, not a one-word escape
    hatch a model can reach for silently.
    """
    open_items = []
    has_any = False
    paused = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if s.upper().startswith("PAUSED"):
                    reason = s[len("PAUSED"):].strip(" \t:：-–—")
                    if len(reason.strip()) >= 3:
                        paused = True
                    continue
                if len(s) < 4 or not s.startswith("- ["):
                    continue
                mark = s[3:4].lower()
                if s[2:5] == "[ ]":
                    has_any = True
                    open_items.append(s)
                elif mark in ("x", "~"):
                    has_any = True
    except FileNotFoundError:
        return [], False, False
    except Exception:
        # Unreadable ledger: treat as "no ledger" -> fail open.
        return [], False, False
    return open_items, has_any, paused
