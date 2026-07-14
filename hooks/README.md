# fable-mode guard hooks

The enforcement layer: turn a few of fable-mode's prose rules into Claude Code
hooks that actually block — ledger-before-delegation and close-verification,
built around this repo's SPEC.md/PROGRESS.md conventions.

## Four hooks + one lint CLI

| Hook | Event | What it does |
|---|---|---|
| `fable_profile_inject.py` | `SessionStart` | When the project has opted in, **auto-inject the tier by model + the six levers + ledger context recovery** (no need to type "use fable mode") |
| `fable_spawn_guard.py` | `PreToolUse` (Agent\|Task\|Workflow) | When opted in: **block a detailed spawn with no ledger** (forces the plan gate) and **block any spawn requesting a model stronger than the session's** (the model ceiling) |
| `fable_fail_streak.py` | `PostToolUse` (Bash) | Advisory, never blocks: at every 3rd **consecutive failing command**, inject the attribution ladder (harness → deployment → product; fix the class via an invariant). Streak state: `$TMPDIR/fable-mode-sessions/<sid>.fails`, reset on success. |
| `fable_close_guard.py` | `Stop` | While the ledger still has unchecked items, **block ending the turn** (cures early stopping / spinning). When all items are checked, **block if any `- [x]` lacks an evidence marker** (`-- evidence:` / `证据:`) — evidence-on-close. |

`fable_lint.py` is **not a hook** — a one-shot CLI (`python3 fable_lint.py <project_dir>`)
for wrap-up or CI: SPEC exists and carries source tags ([measured]/[inferred]/[not-shown]
or the Chinese set), open cards name their acceptance, closed cards carry evidence.
Exit 1 with `FINDING` lines if the discipline leaks.

`_fable_common.py` is the shared helper for all of them (read stdin, walk up to find `.fable/`, parse the ledger, evidence regex, streak store).

## Opt-in signal: the `.fable/` directory (searched upward, bounded at git root)

The four hooks are registered in the global `settings.json` and fire for every
project, every session. "Does the project root have a `.fable/` directory" is
the switch:

- **Has `.fable/`** -> the four hooks take effect.
- **No `.fable/`** -> the four hooks pass through silently, as if absent — they never touch your other projects.

## Per-model tier selection (Profile Injector)

At SessionStart (only when the project has opted in), it reads the `model` field
from the hook input and auto-selects a tier, injecting it as context:

- `model` contains `fable` -> **throughput tier** (aggressive parallel delegation, async non-blocking, bulk offload).
- otherwise / `model` absent -> **conservative tier** (<=5 concurrent, inline-first).
- Override: env var `FABLE_MODE_PROFILE=auto|conservative|throughput`.

It also injects the open items from `.fable/LEDGER.md` for "context recovery"
(aligned with the context-hygiene lever), and the top bullets from the
cross-session lessons file `<config-dir>/fable-lessons.md` (newest first,
bounded to ~5 items / 600 chars; full injections only, so idle/paused sessions
stay frugal; missing file -> silently skipped).
Note: the `model` field is not guaranteed to be present; when absent it safely
defaults to the conservative tier. This is SessionStart-only info (there is no
`$CLAUDE_MODEL` environment variable).

## Ledger format `.fable/LEDGER.md` (checkbox state machine)

```
- [ ] 1. an open card (each card with a machine-checkable acceptance test)
- [x] 2. done -- evidence: pytest 21/21
- [~] 3. not this round -- deferred: reason
PAUSED: reason        <- optional line anywhere: suspend enforcement
```

- `- [ ]` = open, blocks stop. Detailed fan-out requires at least one open
  card — a finished round's closed cards don't unlock new delegation.
- `- [x]` / `- [~]` = closed. A `- [x]` additionally needs a **substantive**
  evidence note (`evidence:` / `verified:` / `证据:` + at least a few concrete
  characters — `evidence: ok` counts as missing) or the close guard blocks
  turn-end.
- `PAUSED: reason` (line prefix, case-insensitive, **reason required** — a bare
  `PAUSED` is ignored so pausing stays attributable) = enforcement off
  **except the model ceiling** (quota protection is not workflow discipline).
  For user-steered work unrelated to the current round; remove the line to
  resume.
- SPEC.md/PROGRESS.md remain the durable design/progress docs; LEDGER.md is only the enforcement-state snapshot of "what I committed to this round."

## Per-task granularity (big projects)

Arming is per-project (`.fable/`), but pressure is per-round via the ledger
state, so small tasks in a big project aren't taxed:

| Ledger state | Guards | Injection |
|---|---|---|
| starting (no cards yet) | design gate armed | full (~1.6KB) |
| **active** (open `- [ ]`) | full enforcement | full + context recovery |
| **idle** (all closed) | close guard quiet; detailed fan-out still needs a new open card | one-liner (~0.4KB) |
| **paused** (`PAUSED: reason` line) | off except model ceiling | one-liner (~0.2KB) |

## Model ceiling (mechanical)

fable-mode's purpose is Fable-5-grade results **without** reaching up to Fable 5,
so the spawn guard blocks any spawn requesting a model **stronger than the
session's** (ranked `haiku < sonnet < opus < fable`):

- Checked on the `model` parameter (Agent/Task) and on `model: '...'` /
  `model = "..."` literals inside Workflow scripts. The regex is key-prefixed,
  so prose like "fable-mode" can never false-positive.
- The session model comes from a per-session cache written at SessionStart by
  the Profile Injector (`$TMPDIR/fable-mode-sessions/<session_id>.txt`, ~20
  bytes, self-cleans after 7 days) — PreToolUse hooks never receive `model`.
- Fail-open: unknown session model or unrecognized requested model -> allowed.
- Opt-out: `FABLE_ESCALATION=on` (you genuinely intend upward deferral).
- Checked before all exemptions — even a small spawn or a fork must not reach
  above the session model.

## Exemptions & safety

- **Small-spawn exemption**: payload < `FABLE_SPAWN_MIN_CHARS` (default 1500 chars) is not blocked.
- **Fork exemption**: a `subagent_type` containing `fork` is not blocked (it inherits full context, no spec tax).
- **Loop-safe**: the close guard passes through when it sees `stop_hook_active`, so you're never trapped.
- **Fail-open**: any hook exception passes through (exit 0) — it never bricks the session.

## Install / register

Easiest: run the installer at the repo root. It resolves its own location,
honors `CLAUDE_CONFIG_DIR`, and merges the hooks into `settings.json`
idempotently (re-run to re-point after a move; `--uninstall` to remove):

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/install.sh"
```

To register by hand instead, merge these four entries into the `hooks` object
of `<config-dir>/settings.json` (don't overwrite the file). The
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}` is expanded by the shell at hook-run time;
use your actual absolute clone path if it differs:

```json
"hooks": {
  "SessionStart": [{"hooks": [{"type": "command",
    "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_profile_inject.py"}]}],
  "PreToolUse": [{"matcher": "Agent|Task|Workflow",
    "hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_spawn_guard.py"}]}],
  "PostToolUse": [{"matcher": "Bash",
    "hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_fail_streak.py"}]}],
  "Stop": [{"hooks": [{"type": "command",
    "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_close_guard.py"}]}]
}
```

Requires `python3` (standard library only, no third-party deps). Then, in a
project, `mkdir .fable` and write `.fable/LEDGER.md` to enable enforcement there.

## Turn enforcement off

Delete the project's `.fable/` directory (or check every card to `- [x]`/`- [~]`).
To disable entirely, remove the hooks block from settings.json.

## Tests

No third-party deps, just run:

```bash
python3 tests/test_guards.py   # 13 cases: opt-in detection, ledger presence, small-spawn/fork exemptions, git-root boundary, loop-safety, fail-open
python3 tests/test_inject.py   #  9 cases: per-model tier, env override, ledger context recovery, JSON envelope, fail-open
```
