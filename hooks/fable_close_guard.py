#!/usr/bin/env python3
"""fable-mode Close Guard  (Stop hook).

Blocks ending the turn while `.fable/LEDGER.md` still has open `- [ ]` items,
so fable-mode can't quietly stop mid-plan (the "rare early-stopping" failure).
Mark items `- [x]` (done+verified) or `- [~] ... -- deferred: reason` to close.

Inert unless a `.fable/LEDGER.md` is found. Loop-safe via stop_hook_active.
Fail-open on any error.

Exit codes: 0 = allow stop; 2 = block stop (stderr shown to Claude).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fable_common import (  # noqa: E402
    read_hook_input, start_dir, find_fable_dir, ledger_path, parse_ledger,
)

MAX_LIST = 12


def main():
    data = read_hook_input()

    # Prevent an infinite stop/continue loop: if we already blocked once and
    # Claude is stopping again, let it through.
    if data.get("stop_hook_active"):
        return 0

    fable_dir = find_fable_dir(start_dir(data))
    if not fable_dir:
        return 0

    path = ledger_path(fable_dir)
    if not os.path.isfile(path):
        return 0  # no ledger -> nothing to enforce

    open_items, _has_any = parse_ledger(path)
    if not open_items:
        return 0  # all closed -> allow stop

    shown = open_items[:MAX_LIST]
    more = len(open_items) - len(shown)
    lines = "\n".join("    " + it for it in shown)
    if more > 0:
        lines += "\n    ... and %d more" % more
    sys.stderr.write(
        "[fable-mode] BLOCKED stop: %d open ledger item(s) in %s\n%s\n"
        "Finish each item and verify it (its acceptance command), then mark "
        "`- [x]`; or if genuinely out of scope, mark `- [~] ... -- deferred: "
        "reason`. Do the work now rather than ending the turn.\n"
        % (len(open_items), path, lines)
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # fail-open: never trap the user in a session
        sys.stderr.write("[fable-mode] close guard error (ignored): %r\n" % e)
        sys.exit(0)
