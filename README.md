# fable-mode

**English** | [简体中文](README.zh-CN.md)

**A work-discipline protocol that makes Opus 4.8 (or any non-frontier model) operate at Fable-5-grade quality.**

fable-mode is a [Claude Code](https://claude.com/claude-code) skill plus a set of
guard hooks. Its premise:

> **output quality = model capability × work discipline**

---

## Quickstart

```bash
# 1. Install the skill (honors CLAUDE_CONFIG_DIR; falls back to ~/.claude)
git clone https://github.com/cozytab/fable5-mode \
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode"

# 2. (optional) register the enforcement hooks — merges into your settings.json,
#    resolves its own path, idempotent:
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/install.sh"
```

```text
# 3. In Claude Code, just ask for it — in any language:
   "use fable mode"   ·   "用 fable 模式"   ·   "do this rigorously, one-shot"
```

```bash
# 4. For a project you're taking seriously, turn on enforcement:
mkdir .fable
printf -- '- [ ] 1. first card (with a machine-checkable acceptance test)\n' > .fable/LEDGER.md
```

The skill works on its own; step 2 is **optional** (it turns the discipline into
hard blocks). Claude replies in **your** language even though the skill is
authored in English.

## Design intent & what it changes

**Why it exists.** Weaker models mostly don't fail by being dumb in the moment;
they fail by *process*: thinking while typing and changing their mind halfway,
declaring "looks right" without running anything, fanning work out with no
verification, and quietly stopping mid-task. Those are process failures, and
process is fixable with structure. Since the "discipline half" of frontier
output is model-independent, you can hand a cheaper model the *working habits* of
a stronger one and recover a real chunk of the gap — paying in orchestration
steps instead of a bigger model.

**What you actually get.**

- Thinking happens in the cheapest phase (a written plan gate), not mid-implementation.
- "Done" means an acceptance command passed — not "looks right."
- Critical output survives an adversarial *refute* pass before it ships.
- Context stays clean across long runs, via external SPEC/PROGRESS memory instead of a bloated transcript.
- The two rules models shirk most — *write a plan before fanning out* and *don't stop with unfinished work* — are enforced by hooks, not hope.
- It's honest about its ceiling: on a real capability wall (a long from-scratch derivation, holding a huge codebase at once, fine aesthetic judgment) it tells you to switch to a stronger model instead of faking it.

**What it does not do.** It won't turn Opus into Fable 5. It closes the
*discipline* gap, not the *capability* gap. The cost is real — more orchestration
steps and slower wall-clock on small tasks — which is exactly why you don't use
it on small tasks. (Net token cost depends on the task; on rework-prone work the
discipline can even come out lower.)

## The six levers

| # | Lever | What it forces |
|---|---|---|
| 1 | **Plan Gate** | Write `docs/SPEC.md` (requirements + approach + task cards, each with a *machine-checkable* acceptance test) before writing code. Concentrate thinking in the cheapest phase. |
| 2 | **Small-card execution** | Each card runs in a fresh context; don't advance until its acceptance command passes; on 2 failures, escalate instead of flailing. |
| 3 | **Adversarial self-check** | Don't "generate and ship." Dispatch independent viewpoints to *refute* critical output; for wide-open problems, generate N approaches + judge + synthesize. |
| 4 | **Real-product verification** | All-green static checks ≠ it works. Run the real product end-to-end each milestone and leave evidence (screenshots, logs, test output). |
| 5 | **Context hygiene** | SPEC + PROGRESS are external memory. Restore state by re-reading them, not by dragging failed-attempt reasoning through a bloated context. |
| 6 | **Checkpoint autonomy** | Long background tasks get a watchdog and resumable checkpoints, so a hang or crash costs at most one card. |

The full protocol lives in **[`SKILL.md`](SKILL.md)** — the text Claude actually reads.

## The enforcement layer (the part that's more than a prompt)

Six levers written as prose still rely on the model's honor. Four hooks turn the
most-shirked rules into hard blocks:

| Hook | Event | Effect |
|---|---|---|
| **Profile Injector** | `SessionStart` | Auto-injects the discipline, **sized to the ledger state** — full during an active round, a one-liner when idle or paused — plus the model-appropriate tier and open-item recovery. |
| **Spawn Guard** | `PreToolUse` (Agent/Task/Workflow) | Blocks a detailed spawn before a ledger exists (forces the plan gate), and blocks any spawn requesting a model **stronger than the session's** — the model ceiling is mechanical, not just prose. |
| **Fail-Streak Reminder** | `PostToolUse` (Bash) | Advisory, never blocks: at every 3rd consecutive failing command it injects the **attribution ladder** (suspect the harness → prove the new code is running → only then debug the product, and fix the class via an invariant) — cures grinding on the wrong layer. |
| **Close Guard** | `Stop` | Blocks ending the turn while the ledger still has unchecked items — cures early stopping / spinning. Also enforces **evidence-on-close**: a `- [x]` card without an `-- evidence:` note blocks the stop ("report evidence, not adjectives" as a hard rule). |

Plus **`hooks/fable_lint.py`** — not a hook but a one-shot CLI: checks the SPEC
carries `[measured]/[inferred]/[not-shown]` source tags, every open card names
its acceptance, every closed card carries evidence. Run it at wrap-up (or in CI):
`python3 hooks/fable_lint.py <project_dir>`.

Design properties that make this safe to register globally:

- **Opt-in per project** via a `.fable/` directory (searched upward, bounded at
  the git root). No `.fable/` → the hooks pass through silently. They never touch
  projects you didn't opt in.
- **Fail-open** — any hook error passes through (exit 0). A bug in a guard can
  never brick your session.
- **Loop-safe** — the close guard honors `stop_hook_active`, so you're never trapped.
- **Exemptions** — small spawns (< 1500 chars) and forks are never blocked.

See **[`hooks/README.md`](hooks/README.md)** for the mechanics.

## Install

**Prerequisites**: [Claude Code](https://claude.com/claude-code), and `python3`
(standard library only — no third-party deps; needed only if you use the hooks).

Your Claude config directory is `$CLAUDE_CONFIG_DIR` if that variable is set,
otherwise `~/.claude`. Everything below derives from it, so it works no matter
where your config lives.

### Option A — automated (recommended; this is what an AI can run for you)

```bash
git clone https://github.com/cozytab/fable5-mode \
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode"
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/install.sh"
```

`install.sh` **resolves its own location** (so the hook paths are correct no
matter where you cloned it), honors `CLAUDE_CONFIG_DIR`, and **merges** the three
hooks into your `settings.json` without disturbing existing config. It's
idempotent — re-run it after moving the skill and it re-points the paths. Remove
the hooks any time with `bash install.sh --uninstall`.

Or just tell Claude Code:

> Install the skill at https://github.com/cozytab/fable5-mode by following its README.

**Updating**: after `git pull`, re-run `install.sh`. A new version can add hook
events (e.g. a `PostToolUse` hook), and only the installer updates your
`settings.json` — a plain `git pull` ships the files but won't register new
hooks. It's idempotent, so re-running is always safe.

### Option B — manual

Clone as above, then **merge** these four entries into the `hooks` object of
`<config-dir>/settings.json` (don't overwrite the file; if you already have a
`hooks` key, add these under it). Use the absolute path to where you actually
cloned it — the `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` below is expanded by the
shell at hook-run time:

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

The skill alone is enough to trigger fable-mode by asking for it; skip the hooks
if you only want the protocol.

### For AI assistants installing this

When a user asks you to install fable-mode from this repo:

1. Config dir = `$CLAUDE_CONFIG_DIR` if set, else `~/.claude`.
2. `git clone` the repo into `<config-dir>/skills/fable-mode`.
3. Run `bash <config-dir>/skills/fable-mode/install.sh` — it merges the hooks
   idempotently and resolves paths itself. If you instead register hooks by
   editing `settings.json` yourself, **merge** into the existing `hooks` object
   (never overwrite the file) and use the **absolute** clone path — do not
   hardcode `~/.claude` if the user relocated their config.
4. Tell the user the hooks are optional and stay inert until a project has a
   `.fable/` directory.

## Use

**Trigger the skill by asking for it by name** — "use fable mode", "work like
Fable 5", "rigorous mode", or the Chinese equivalents ("用 fable 模式",
"严谨模式"). It deliberately does **not** auto-trigger just because a task is
big or important — no surprise process tax; at most it may *offer* to enable
itself. The other explicit path is a project armed with `.fable/`, where the
hooks carry the discipline in automatically.

**Enable the mechanical enforcement** on a project you're taking seriously:

```bash
mkdir .fable
cat > .fable/LEDGER.md <<'EOF'
- [ ] 1. first card (with a machine-checkable acceptance test)
- [ ] 2. second card
EOF
```

From then on, in that project: sessions auto-load the discipline and the right
tier; you can't dispatch a detailed agent without a ledger; you can't end a turn
with unchecked cards. Mark cards `- [x]` (done + verified) or
`- [~] ... -- deferred: reason` to close them. To turn enforcement off, check
everything or `rm -rf .fable`.

**Big project, small tasks?** Enforcement is per-*round*, not per-*keystroke*:
with all cards closed (idle) the guards stay quiet and quick fixes flow freely
with near-zero injection. Mid-round, drop a `PAUSED: reason` line into
`.fable/LEDGER.md` to do unrelated work without being nagged (the model ceiling
stays active); remove it to resume the round.

## Concurrency tiers

fable-mode's concurrency isn't a fixed number.

- **Conservative (default)** — cap of ≤5 concurrent subagents, a local rate-limit
  guardrail. Right for everyday, quota-sensitive, quality-first work.
- **Throughput (opt-in)** — dispatch parallel subagents readily, communicate
  async, don't block. No fixed cap; field deployments range 10–500+. It trades
  more tokens for throughput and risks rate limits — so it's enabled only when you
  ask, or auto-selected when the running model is Fable 5.

The Profile Injector picks the tier automatically by model
(`FABLE_MODE_PROFILE=auto|conservative|throughput` overrides).

**Model routing (capability-matched)**: neither "never downgrade" nor "offload
to cheap" is right. fable-mode routes by what the card demands — design,
debugging and **all verification** stay on the session model; a well-specified
implementation card may drop one tier; mechanical gather/format work goes to a
cheap tier at low effort. This mirrors Anthropic's own practice (Opus-class lead
+ Sonnet-class subagents in their research system, +90.2% over single-agent).
What makes downgrading safe is the safety net: only cards with machine-checkable
acceptance are downgraded, two failed acceptances escalate the model tier —
**capped at the session model** (the top of the ladder is pulling the card back
inline, never a stronger model: fable-mode exists to get Fable-5-grade results
*without* Fable 5, so it never quietly reaches upward) — and the verifier is
always at least as strong as the implementer. When unsure, inherit the session
model.

## The Fable 5 habit set

Beyond the six levers, the skill transplants the concrete behaviors Anthropic
documents for Fable 5 — so any model in a fable-mode project inherits them:
ground every progress claim in a tool result; never end a turn on a promise you
could act on; lead with the outcome; pause only where the user is genuinely
needed; assessment before action; fresh-context verifiers over self-critique;
model & effort routed by task (verification never downgraded); pass the *why*
along when delegating; keep a lessons file; **act once you have enough
information** (no re-litigating settled decisions); **do the simplest thing
that works** (no unrequested refactors or defensive code); write the final
summary as a **re-grounding** for a reader who saw none of the work; **triage
multi-part requests** so no sub-ask is silently dropped; write code that blends
into the surrounding file. The highest-value habits are auto-injected into
every fable-mode session by the Profile Injector.

Starter skeletons live in [`templates/`](templates/) — SPEC, LEDGER, PROGRESS,
and an engine-neutral fresh-eyes [verifier prompt](templates/VERIFIER_PROMPT.md).

**Cross-session memory**: lessons that transcend one project go to
`<config-dir>/fable-lessons.md` (one bullet each, newest first). The Profile
Injector surfaces the top few in every armed session — a lesson learned once
stops being relearned, which is one of the documented Fable 5 advantages this
skill reproduces mechanically.

## How close to Fable 5 does it actually get?

Honest answer: frontier output = capability × discipline, and this skill can
only transplant the **discipline** half — but it transplants essentially all of
it, and mechanically rather than as prose promises: the plan gate, per-card
acceptance, adversarial verification, evidence-on-close, the attribution
ladder, cross-session lessons, and the model ceiling are enforced by hooks and
lint, not hope. What it cannot give a weaker model: single very long reasoning
chains, holding a huge codebase in mind at once, frontier-grade visual
precision and taste. For those it degrades gracefully — decompose, best-of-N +
judge, tools as ground truth — and tells you what remains uncertain instead of
faking it. In practice that means: on well-specified, verifiable development
work the gap narrows dramatically; on raw-capability walls it narrows the
honest way — by saying so.

**Why a skill + hooks, not a plugin or agent?** A plugin restructure would add
distribution convenience but no new enforcement capability, and we don't ship
forms we can't verify end-to-end; an "agent" can only advise, not block. The
current form installs with one clone + one script and is verified on a real
machine. Plugin packaging is deferred, not rejected.

## No stronger model? It degrades, never stalls

fable-mode is honest about capability walls — but "switch to Fable 5" is a dead
end if you can't run Fable 5. So a non-Fable session is automatically told **not
to defer hard steps to a stronger model or stall waiting for one**. Instead it
compensates on the model you have: decompose the wall into smaller verifiable
steps, best-of-N + a judge, make tools/tests the ground truth, and flag residual
risk instead of blocking. If you *do* have a stronger tier to hand off to, set
`FABLE_ESCALATION=on`.

## Layout

```
fable-mode/
├── SKILL.md              # the protocol Claude reads (the six levers, tiers, red lines)
├── README.md             # this file
├── README.zh-CN.md       # 简体中文
├── install.sh            # merge/remove the hooks in settings.json (path-resolving, idempotent)
├── templates/            # SPEC / LEDGER / PROGRESS skeletons + fresh-eyes verifier prompt
├── hooks/
│   ├── README.md         # hook mechanics, ledger format, install
│   ├── _fable_common.py  # shared helpers (stdin, upward .fable/ search, ledger parse)
│   ├── fable_profile_inject.py   # SessionStart: per-model tier + context recovery
│   ├── fable_spawn_guard.py      # PreToolUse: design gate (open card required) + model ceiling
│   ├── fable_fail_streak.py      # PostToolUse(Bash): attribution-ladder reminder on fail streaks
│   ├── fable_lint.py             # not a hook: one-shot discipline lint CLI
│   └── fable_close_guard.py      # Stop: open cards / hollow evidence → block turn end
└── tests/
    ├── test_guards.py    # spawn/close guards, model ceiling, PAUSED, evidence, fail-streak, lint
    ├── test_inject.py    # per-state injection, tiers, routing, escalation policy
    └── test_install.py   # install.sh: fresh/merge/idempotent/re-point/uninstall
```

## Tests

No third-party dependencies:

```bash
python3 tests/test_guards.py    # opt-in detection, ledger presence, exemptions, git-root boundary, loop-safety, fail-open
python3 tests/test_inject.py    # per-model tier, env override, context recovery, JSON envelope, fail-open
python3 tests/test_install.py   # install.sh: fresh, merge, idempotent, re-point, uninstall, bad-JSON refusal
```

## License

[MIT](LICENSE) © 2026 cozytab.

You may use, copy, modify, merge, publish, distribute, sublicense, and sell it —
including commercially, and including in closed-source work. **The only
requirement**: keep the copyright notice and the MIT permission text (i.e. the
`LICENSE` file) in all copies or substantial portions. It's provided "as is",
with no warranty and no liability on the author.
