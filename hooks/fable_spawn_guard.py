#!/usr/bin/env python3
"""fable-mode Spawn Guard  (PreToolUse on Agent | Task | Workflow).

Blocks a *detailed* delegation when the project has opted into fable-mode
(`.fable/` dir present) but no `.fable/LEDGER.md` with task cards exists yet.
Intent: enforce the design gate -- write the SPEC + ledger before fanning out.

Inert unless a `.fable/` dir is found. Small spawns and forks are exempt.
Fail-open on any error.

Exit codes: 0 = allow the tool call; 2 = block (stderr shown to Claude).
Env:
  FABLE_SPAWN_MIN_CHARS  minimum payload length to be considered "detailed"
                         (default 1500). Below this, always allowed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fable_common import (  # noqa: E402
    read_hook_input, start_dir, find_fable_dir, ledger_path, parse_ledger,
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


def main():
    data = read_hook_input()
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    fable_dir = find_fable_dir(start_dir(data))
    if not fable_dir:
        return 0  # project not opted in -> inert

    if is_fork(tool_input):
        return 0  # forks inherit full context; exempt from the spec tax

    try:
        threshold = int(os.environ.get("FABLE_SPAWN_MIN_CHARS", "1500"))
    except ValueError:
        threshold = 1500
    if payload_len(tool_name, tool_input) < threshold:
        return 0  # small delegation -> exempt

    _open, has_any = parse_ledger(ledger_path(fable_dir))
    if has_any:
        return 0  # ledger exists with task cards -> allowed

    sys.stderr.write(
        "[fable-mode] BLOCKED: this project is in fable-mode (.fable/ present) "
        "but .fable/LEDGER.md has no task cards yet.\n"
        "Before fanning out a detailed subagent/Workflow, write the design gate:\n"
        "  1. docs/SPEC.md  -- requirements + approach + task-card list\n"
        "  2. .fable/LEDGER.md  -- one checkbox per card:\n"
        "       - [ ] 1. <card>  (each card needs a machine-checkable acceptance test)\n"
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
