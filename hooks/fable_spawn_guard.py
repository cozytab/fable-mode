#!/usr/bin/env python3
"""fable-mode Spawn Guard  (PreToolUse on Agent | Task | Workflow).

Two enforcement duties when the project has opted in (`.fable/` dir present):

1. Design gate: block a *detailed* delegation while the ledger has no OPEN
   task cards (write the SPEC + a live round's cards before fanning out;
   closed cards from a finished round don't unlock new fan-out).
   Small spawns and forks are exempt.
2. Model ceiling: block any spawn that requests a model STRONGER than the
   session's (haiku < sonnet < opus < fable) — fable-mode exists to get
   Fable-5-grade results without reaching upward. The session model comes from
   the Profile Injector's per-session cache; unknown either side -> fail-open.
   FABLE_ESCALATION=on disables the ceiling.

Inert unless a `.fable/` dir is found. Fail-open on any error.

Exit codes: 0 = allow the tool call; 2 = block (stderr shown to Claude).
Env:
  FABLE_SPAWN_MIN_CHARS  minimum payload length to be considered "detailed"
                         (default 1500). Below this, the design gate passes.
  FABLE_ESCALATION       "on" allows spawning above the session model.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fable_common import (  # noqa: E402
    read_hook_input, start_dir, find_fable_dir, ledger_path, parse_ledger,
    model_tier, load_session_model,
)


def payload_len(tool_name, tool_input):
    if not isinstance(tool_input, dict):
        return 0
    parts = []
    for key in ("prompt", "script", "description"):
        v = tool_input.get(key)
        if isinstance(v, str):
            parts.append(v)
    return len("\n".join(parts))


def is_fork(tool_input):
    if not isinstance(tool_input, dict):
        return False
    for key in ("subagent_type", "agentType", "agent_type"):
        v = tool_input.get(key)
        if isinstance(v, str) and "fork" in v.lower():
            return True
    return False


# Key-prefixed on purpose: matches model: 'fable' / model="claude-fable-5"
# inside a Workflow script, but can NOT false-positive on prose like
# "fable-mode" (no model key in front of it).
_SCRIPT_MODEL_RE = re.compile(r"""model\s*[:=]\s*['"]([^'"]+)['"]""")


def requested_tier(tool_name, tool_input):
    """Strongest model tier explicitly requested by this spawn, or None."""
    if not isinstance(tool_input, dict):
        return None
    tiers = []
    v = tool_input.get("model")
    if isinstance(v, str):
        t = model_tier(v)
        if t is not None:
            tiers.append((t, v))
    if tool_name == "Workflow":
        s = tool_input.get("script")
        if isinstance(s, str):
            for match in _SCRIPT_MODEL_RE.finditer(s):
                t = model_tier(match.group(1))
                if t is not None:
                    tiers.append((t, match.group(1)))
    return max(tiers) if tiers else None


def main():
    data = read_hook_input()
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    fable_dir = find_fable_dir(start_dir(data))
    if not fable_dir:
        return 0  # project not opted in -> inert

    # Model ceiling — checked before all exemptions: even a small spawn or a
    # fork must not request a model stronger than the session's.
    if os.environ.get("FABLE_ESCALATION", "auto").lower() != "on":
        sess_model = load_session_model(data.get("session_id"))
        sess_tier = model_tier(sess_model)
        req = requested_tier(tool_name, tool_input)
        if sess_tier is not None and req is not None and req[0] > sess_tier:
            sys.stderr.write(
                "[fable-mode] BLOCKED: this spawn requests model '%s', which is "
                "STRONGER than the session model '%s'. fable-mode's purpose is "
                "Fable-5-grade results WITHOUT reaching upward — the escalation "
                "ceiling is the session model. Omit the model param to inherit, "
                "or pull the card back inline. Set FABLE_ESCALATION=on only if "
                "upward deferral is genuinely intended.\n" % (req[1], sess_model)
            )
            return 2

    if is_fork(tool_input):
        return 0  # forks inherit full context; exempt from the spec tax

    try:
        threshold = int(os.environ.get("FABLE_SPAWN_MIN_CHARS", "1500"))
    except ValueError:
        threshold = 1500
    if payload_len(tool_name, tool_input) < threshold:
        return 0  # small delegation -> exempt

    _open, has_any, paused = parse_ledger(ledger_path(fable_dir))
    if paused:
        return 0  # round paused -> design gate off (ceiling stayed active above)
    if _open:
        return 0  # a live round with open cards -> allowed
    # No OPEN cards: either no ledger at all, or only closed cards from a
    # finished round. Stale closed cards must not unlock new fan-out — a
    # detailed delegation is round work, so it needs a live card first.
    sys.stderr.write(
        "[fable-mode] BLOCKED: this project is in fable-mode (.fable/ present) "
        "but .fable/LEDGER.md has no OPEN task cards for a current round"
        " (closed cards from a finished round don't count).\n"
        "Before fanning out a detailed subagent/Workflow, write the design gate:\n"
        "  1. docs/SPEC.md  -- requirements + approach + task-card list\n"
        "  2. .fable/LEDGER.md  -- one checkbox per card:\n"
        "       - [ ] 1. <card>  (each card needs a machine-checkable acceptance test)\n"
        "Close the load-bearing unknowns with targeted probes first and tag SPEC "
        "decisions [measured]/[inferred]/[not-shown]; cards close only with an "
        "`-- evidence:` note.\n"
        "Then retry the delegation. (Small spawns < %d chars and forks are exempt.)\n"
        % threshold
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # fail-open: never brick the session
        sys.stderr.write("[fable-mode] spawn guard error (ignored): %r\n" % e)
        sys.exit(0)
