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
import sys


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


def parse_ledger(path):
    """Return (open_items, has_any) for a ledger file.

    A ledger line is a markdown checkbox: `- [ ] ...`, `- [x] ...`, `- [~] ...`
    (case-insensitive on x). `open_items` is the list of `- [ ]` line texts.
    `has_any` is True if the file has at least one checkbox line at all.
    """
    open_items = []
    has_any = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if len(s) < 4 or not s.startswith("- ["):
                    continue
                mark = s[3:4].lower()
                if s[2:5] == "[ ]":
                    has_any = True
                    open_items.append(s)
                elif mark in ("x", "~"):
                    has_any = True
    except FileNotFoundError:
        return [], False
    except Exception:
        # Unreadable ledger: treat as "no ledger" -> fail open.
        return [], False
    return open_items, has_any
