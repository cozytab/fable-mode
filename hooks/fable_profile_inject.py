#!/usr/bin/env python3
"""fable-mode Profile Injector  (SessionStart hook).

When a project has opted into fable-mode (`.fable/` dir present), auto-inject
the fable-mode discipline + the model-appropriate tier at session start, so you
don't have to type "use fable mode" every time. Also re-surfaces open ledger
items for context recovery on resume.

Inert unless a `.fable/` dir is found  ->  keeps fable-mode opt-in at the
project level while auto-selecting the tier at the model level.
Fail-open: any error  ->  exit 0 with no output.

Tier selection (env FABLE_MODE_PROFILE overrides: auto|conservative|throughput):
  model contains "fable"  ->  throughput (aggressive parallel delegation)
  otherwise / model absent ->  conservative (<=5 concurrent, inline-first)

Graceful degradation: a conservative (non-Fable) session also gets a
"don't defer to a stronger model, don't stall" instruction, so work never gets
stuck waiting for a Fable 5 the user can't run. Set FABLE_ESCALATION=on to opt
out (you genuinely have a stronger tier available).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fable_common import (  # noqa: E402
    read_hook_input, start_dir, find_fable_dir, ledger_path, parse_ledger,
)

SKILL = "~/.claude/skills/fable-mode/SKILL.md"
MAX_LIST = 12


def choose_profile(model):
    env = os.environ.get("FABLE_MODE_PROFILE", "auto").lower()
    if env in ("conservative", "throughput"):
        return env
    return "throughput" if "fable" in (model or "").lower() else "conservative"


def build_context(profile, model, fable_dir):
    m = model or "unknown"
    if profile == "throughput":
        tier = (
            "Current model %s -> THROUGHPUT tier: delegate parallel subagents "
            "aggressively, communicate async (don't block on each return); "
            "still enforce ledger-before-delegation and staged fresh-eyes "
            "verification. Subagents inherit this session's model — do NOT "
            "downgrade them (solving the problem outranks saving tokens; "
            "downgrade only trivially-mechanical, machine-checkable subtasks). "
            "The cost (~15x tokens / rate limits) is known and accepted." % m
        )
    else:
        tier = (
            "Current model %s -> CONSERVATIVE tier: cap concurrency at 5, "
            "inline-first, don't split unless it clearly helps, quality first; "
            "if unsure whether delegation preserves quality, do it yourself. "
            "Subagents inherit this session's model — never a weaker one." % m
        )

    lines = [
        "[fable-mode] This project has fable-mode enabled (.fable/ detected). "
        "Follow the six levers in %s." % SKILL,
        tier,
        "Design gate: before writing code, produce docs/SPEC.md (requirements + "
        "approach + task cards, each with a machine-checkable acceptance test), "
        "and record this round's committed cards in .fable/LEDGER.md (checkbox "
        "state machine - [ ]/- [x]/- [~]). The guard hooks block 'spawning an "
        "agent with no ledger' and 'ending the turn with unchecked ledger items'.",
        "Fable-5 habits (all models): (1) audit every progress claim against a "
        "tool result before reporting it — unverified means say 'unverified'; "
        "(2) before ending the turn, check your last paragraph — if it's a "
        "plan/promise/next-steps you could act on, act now with tool calls; "
        "(3) lead with the outcome; be selective, not compressed.",
    ]

    # Graceful degradation: a non-Fable session assumes no stronger tier to
    # defer to, so tell the model to never stall/hand off. FABLE_ESCALATION=on
    # opts back in (you genuinely have a stronger model available).
    if profile == "conservative" and \
            os.environ.get("FABLE_ESCALATION", "auto").lower() != "on":
        lines.append(
            "No stronger model is assumed available this session: do NOT defer "
            "hard steps to Fable 5 or stall waiting for a model you can't run. "
            "Instead decompose the hard part into smaller verifiable steps, use "
            "best-of-N + a judge, make tools/tests the ground truth, and flag "
            "residual risk instead of blocking. (Set FABLE_ESCALATION=on if you "
            "do have a stronger tier to defer to.)"
        )

    # Context recovery: surface open ledger items on (re)start.
    try:
        open_items, _ = parse_ledger(ledger_path(fable_dir))
    except Exception:
        open_items = []
    if open_items:
        shown = open_items[:MAX_LIST]
        more = len(open_items) - len(shown)
        recap = "Context recovery: the ledger still has %d open item(s):\n" % len(open_items)
        recap += "\n".join("  " + it for it in shown)
        if more > 0:
            recap += "\n  ... and %d more" % more
        lines.append(recap)

    return "\n".join(lines)


def main():
    data = read_hook_input()
    fable_dir = find_fable_dir(start_dir(data))
    if not fable_dir:
        return 0  # not opted in -> stay silent (preserve on-demand)

    profile = choose_profile(data.get("model"))
    context = build_context(profile, data.get("model"), fable_dir)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # fail-open: never disrupt session start
        sys.stderr.write("[fable-mode] profile inject error (ignored): %r\n" % e)
        sys.exit(0)
