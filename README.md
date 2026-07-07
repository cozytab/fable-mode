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
git clone https://github.com/cozytab/fable-mode \
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

Six levers written as prose still rely on the model's honor. Three hooks turn the
most-shirked rules into hard blocks:

| Hook | Event | Effect |
|---|---|---|
| **Profile Injector** | `SessionStart` | Auto-injects the discipline + the model-appropriate concurrency tier + recovers open ledger items — no need to type "use fable mode." |
| **Spawn Guard** | `PreToolUse` (Agent/Task/Workflow) | Blocks dispatching a detailed subagent/Workflow before a ledger exists — forces the plan gate. |
| **Close Guard** | `Stop` | Blocks ending the turn while the ledger still has unchecked items — cures early stopping / spinning. |

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
git clone https://github.com/cozytab/fable-mode \
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode"
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/install.sh"
```

`install.sh` **resolves its own location** (so the hook paths are correct no
matter where you cloned it), honors `CLAUDE_CONFIG_DIR`, and **merges** the three
hooks into your `settings.json` without disturbing existing config. It's
idempotent — re-run it after moving the skill and it re-points the paths. Remove
the hooks any time with `bash install.sh --uninstall`.

Or just tell Claude Code:

> Install the skill at https://github.com/cozytab/fable-mode by following its README.

### Option B — manual

Clone as above, then **merge** these three entries into the `hooks` object of
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

**Trigger the skill** by asking for it in either language — "use fable mode",
"work like Fable 5", "highest quality, do it right the first time", or the
Chinese equivalents ("用 fable 模式", "严谨模式", "一次做对"). It also triggers
when you hand over a substantial task and ask for it done right the first time.

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

**Model parity**: on either tier, subagents inherit the session's model —
fable-mode never silently downgrades a subagent. Solving the problem outranks
saving tokens; a weak subagent that flails costs more than it saves. Downgrading
is a narrow, explicit exception for trivially mechanical, machine-checkable
subtasks only — never design, non-trivial implementation, debugging, or
verification.

## The Fable 5 habit set

Beyond the six levers, the skill transplants the concrete behaviors Anthropic
documents for Fable 5 — so any model in a fable-mode project inherits them:
ground every progress claim in a tool result; never end a turn on a promise you
could act on; lead with the outcome; pause only where the user is genuinely
needed; assessment before action; fresh-context verifiers over self-critique;
effort routed by task (max = judge, high = build, low = gather — effort, never
a weaker model); pass the *why*
along when delegating; keep a lessons file. The three highest-value habits are
auto-injected into every fable-mode session by the Profile Injector.

Starter skeletons live in [`templates/`](templates/) — SPEC, LEDGER, PROGRESS,
and an engine-neutral fresh-eyes [verifier prompt](templates/VERIFIER_PROMPT.md).

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
│   ├── fable_spawn_guard.py      # PreToolUse: no ledger → block detailed spawns
│   └── fable_close_guard.py      # Stop: open ledger items → block turn end
└── tests/
    ├── test_guards.py    # 13 cases
    ├── test_inject.py    #  9 cases
    └── test_install.py   # 13 cases (install.sh: fresh/merge/idempotent/re-point/uninstall)
```

## Tests

No third-party dependencies:

```bash
python3 tests/test_guards.py    # opt-in detection, ledger presence, exemptions, git-root boundary, loop-safety, fail-open
python3 tests/test_inject.py    # per-model tier, env override, context recovery, JSON envelope, fail-open
python3 tests/test_install.py   # install.sh: fresh, merge, idempotent, re-point, uninstall, bad-JSON refusal
```

## License

No license yet — © 2026 cozytab, all rights reserved. Ask before reusing.
