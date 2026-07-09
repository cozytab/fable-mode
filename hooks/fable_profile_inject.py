#!/usr/bin/env python3
"""fable-mode Profile Injector  (SessionStart hook).

When a project has opted into fable-mode (`.fable/` dir present), inject the
discipline at session start — sized to the ledger state, so a big project's
small tasks aren't taxed:

  starting  (.fable/ but no task cards)  -> full injection (guide the round)
  active    (ledger has open `- [ ]`)    -> full injection + context recovery
  idle      (all cards closed)           -> minimal one-liner; quick work flows
  paused    (a `PAUSED` line in ledger)  -> one-liner; enforcement off except
                                            the model ceiling

Also caches {session_id -> model} so the spawn guard can enforce the model
ceiling (PreToolUse hooks never receive `model`).

Inert unless `.fable/` is found. Fail-open: any error -> exit 0, no output.
Tier: model contains "fable" -> throughput, else conservative
(env FABLE_MODE_PROFILE=auto|conservative|throughput overrides).
FABLE_ESCALATION=on marks a stronger tier as genuinely available.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fable_common import (  # noqa: E402
    read_hook_input, start_dir, find_fable_dir, ledger_path, parse_ledger,
    save_session_model,
)

# resolved from this file's real location, correct wherever the skill is cloned
SKILL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md")
MAX_LIST = 12


def choose_profile(model):
    env = os.environ.get("FABLE_MODE_PROFILE", "auto").lower()
    if env in ("conservative", "throughput"):
        return env
    return "throughput" if "fable" in (model or "").lower() else "conservative"


def build_context(profile, model, ledger_state, open_items):
    m = model or "unknown"

    if ledger_state == "paused":
        return (
            "[fable-mode] Round PAUSED (.fable/LEDGER.md has a PAUSED line): "
            "enforcement is off except the model ceiling (never spawn above "
            "this session's model). Remove the PAUSED line to resume the round."
        )

    if ledger_state == "idle":
        return (
            "[fable-mode] Project armed, ledger idle — quick tasks flow "
            "freely, no process tax. For the next substantial task, follow "
            "%s: SPEC + task cards in .fable/LEDGER.md first (a detailed "
            "fan-out needs a live open card). Always: audit every progress "
            "claim against a tool result; don't end the turn on an actionable "
            "promise; lead with the outcome. Never spawn a subagent above "
            "this session's model." % SKILL
        )

    # starting / active -> full injection
    if profile == "throughput":
        tier = (
            "Current model %s -> THROUGHPUT tier: delegate parallel subagents "
            "aggressively, communicate async (don't block on each return); "
            "still enforce ledger-before-delegation and staged fresh-eyes "
            "verification. Cost (~15x tokens / rate limits) is accepted." % m
        )
    else:
        tier = (
            "Current model %s -> CONSERVATIVE tier: cap concurrency at 5, "
            "inline-first, don't split unless it clearly helps; if unsure "
            "delegation preserves quality, do it yourself." % m
        )

    lines = [
        "[fable-mode] This project has fable-mode enabled (.fable/ detected). "
        "Follow the six levers in %s." % SKILL,
        tier,
        "Model routing: design/debugging/verification stay on this session's "
        "model; a well-specified implementation card (machine-checkable "
        "acceptance) may drop one tier; mechanical work goes cheap at low "
        "effort. Two failed acceptances -> escalate, CAPPED AT this session's "
        "model (top of the ladder is pulling the card back inline — never "
        "spawn above the session model); the verifier must be at least as "
        "strong as the implementer. When unsure, inherit the session model.",
        "Design gate: docs/SPEC.md (requirements + approach + task cards, "
        "each with machine-checkable acceptance) and cards in "
        ".fable/LEDGER.md (- [ ]/- [x]/- [~]; a `PAUSED: reason` line "
        "suspends enforcement for unrelated work — bare PAUSED is ignored). "
        "Before designing, close the load-bearing unknowns with targeted "
        "probes; tag SPEC decisions [measured]/[inferred]/[not-shown]. "
        "Guards block spawning without OPEN cards, stopping with open cards, "
        "and checking a card `- [x]` without a substantive `-- evidence:` "
        "note.",
        "Fable-5 habits: (1) audit every progress claim against a tool "
        "result — unverified means say 'unverified'; (2) don't end the turn "
        "on an actionable plan/promise — act now; (3) lead with the outcome; "
        "be selective, not compressed; (4) desk-check before first run "
        "(re-derive key constants from source evidence); (5) on repeated "
        "failure walk the attribution ladder: harness -> deployment -> "
        "product, then fix the class via an invariant; (6) if the product "
        "can't be driven end-to-end, add a deterministic test hook and "
        "drive it — testability is a product feature; (7) declare workflow "
        "deviations in one line, never silently comply or deviate.",
    ]

    if profile == "conservative" and \
            os.environ.get("FABLE_ESCALATION", "auto").lower() != "on":
        lines.append(
            "No stronger model is assumed available: do NOT defer hard steps "
            "to Fable 5 or stall for a model you can't run — decompose into "
            "verifiable steps, best-of-N + judge, tools/tests as ground "
            "truth, flag residual risk instead of blocking. "
            "(FABLE_ESCALATION=on if a stronger tier truly exists.)"
        )

    if open_items:
        shown = open_items[:MAX_LIST]
        more = len(open_items) - len(shown)
        recap = ("Context recovery: the ledger still has %d open item(s):\n"
                 % len(open_items))
        recap += "\n".join("  " + it for it in shown)
        if more > 0:
            recap += "\n  ... and %d more" % more
        lines.append(recap)

    return "\n".join(lines)


def main():
    data = read_hook_input()
    # Cache session model for the spawn guard's model ceiling — unconditional
    # (a project may opt in mid-session), tiny, best-effort.
    save_session_model(data.get("session_id"), data.get("model"))
    fable_dir = find_fable_dir(start_dir(data))
    if not fable_dir:
        return 0  # not opted in -> stay silent (preserve on-demand)

    open_items, has_any, paused = parse_ledger(ledger_path(fable_dir))
    if paused:
        state = "paused"
    elif open_items:
        state = "active"
    elif has_any:
        state = "idle"
    else:
        state = "starting"

    profile = choose_profile(data.get("model"))
    context = build_context(profile, data.get("model"), state, open_items)
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
