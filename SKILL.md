---
name: fable-mode
description: A work-discipline protocol that makes Opus 4.8 (or any non-frontier model) operate at Fable-5-grade quality. Core idea — output quality = model capability x work discipline: spend extra orchestration to buy single-pass quality via six levers (plan gate, small-card execution, adversarial self-check, real-product verification, context hygiene, checkpoint autonomy). Activate ONLY on an explicit request — the user names the mode ("use fable mode", "enable fable-mode", "work like Fable 5", "rigorous mode", or the Chinese "用 fable 模式"、"开 fable-mode"、"像 Fable 5 一样做"、"严谨模式") — or when the project is already armed with a `.fable/` directory (the hooks handle that). Do not auto-trigger on a task merely being large, important, or quality-sensitive, and not on generic phrases like "do it well / 最高质量 / 别偷懒"; if a task looks like it would benefit, ask the user whether to enable fable-mode instead of assuming.
triggers:
  - "fable mode"
  - "fable-mode"
  - "use fable mode"
  - "work like Fable 5"
  - "rigorous mode"
  - "fable 模式"
  - "开 fable-mode"
  - "像 Fable 5 一样做"
  - "严谨模式"
---

# fable-mode (Fable-grade work-discipline protocol)

You are now in fable-mode. Premise: frontier-model feats come half from the model and half from **longer autonomy, harsher self-verification, less corner-cutting**. That second half is model-independent — this protocol supplies it. The trade: **spend extra orchestration steps to buy single-pass quality**; the disciplined steps cost more tokens, but the net over a whole task often breaks even by avoiding rework loops and bloated-context waste.

## When to use / not use

- **Activation is explicit-only**: enter this mode when the user asks for it by name, or when the project carries a `.fable/` directory. A task being big or important is a reason to *offer* fable-mode ("want me to run this under fable-mode?"), never to silently enter it.
- **Use** (once activated): substantial dev tasks (features, projects, clones, refactors), must-be-right deliverables, multi-file changes, research reports.
- **Don't use**: single-file tweaks, Q&A, small tasks verifiable at a glance — just do them. **Discipline is per-task, not per-project**: inside a fable-mode project a quick fix is still just a quick fix (guards stay quiet when the ledger is idle or paused — see Enforcement).
- **Honest boundary**: real capability walls exist — a single very long reasoning chain, holding a huge codebase at once, strong aesthetic judgment. If a stronger model is available, say so plainly and let the user decide. If not (the common case), degrade gracefully — next section.
- **Tool-reliability red line**: web-fetch tools can hang without timeout and stall a Workflow. Scraping subagents use `curl --max-time`, never WebFetch; long Workflows get a watchdog.

## When no stronger model is available

Never stall, hand off, or end the turn waiting for a model you can't run:

- **Decompose the wall** into smaller steps that each fit the current model; verify each.
- **Best-of-N + judge**: several independent attempts approximate one stronger pass.
- **Tools as ground truth**: run code/tests/REPL instead of deriving perfectly; fetch a reference implementation rather than re-deriving.
- **Flag residual risk and deliver** — state what's uncertain and why; never leave the task stuck.

(Set `FABLE_ESCALATION=on` only if a stronger tier genuinely exists to defer to.)

## The six levers (execute in order)

### 1. Plan Gate
Before code, write `docs/SPEC.md`: requirements, approach, **task cards** (skeletons in `templates/`). Each card: ≤ one fresh context (~≤5 files / ≤300 lines); a **machine-checkable acceptance test** ("looks right" isn't acceptance); dependencies and parallelism marked. Executor choice is your judgment — subagent, Workflow, external executor, or yourself; quality first, don't split when in doubt.

**Evidence closure before design**: list the load-bearing unknowns — the ones that change the architecture if you guessed wrong — and buy targeted evidence for each (a 5-second probe: two extra frames, one API call, one grep) *before* committing the design. Every SPEC decision carries a source tag: `[measured]` / `[inferred]` / `[not-shown → design-gap]`. Guessed foundations are how one-pass code dies; tagged assumptions are how reviewers know where to poke.

### 2. Small-card execution + per-card acceptance
Each card runs in a **fresh context**, fed only the relevant SPEC excerpt — no reasoning garbage from prior cards. Run acceptance the moment it's done; **don't advance until it passes**. Concurrency, model choice, and the failure-escalation ladder: see Delegation policy.

### 3. Adversarial self-check
Important output is never "generate and ship". Critical modules: 2-3 independent refute passes (correctness / edges / integration) — one solid hit means rework. Wide solution spaces: N approaches + judge + synthesize. **Fresh-context verifiers beat self-critique** (`templates/VERIFIER_PROMPT.md`); verifier prompts say "assume broken, falsify hard", never "take a look".

**Desk-check before first run**: after drafting a large unit, re-derive the critical constants from the source evidence (layout proportions, units, coordinate mappings, state-machine edges) instead of trusting the draft, and probe interaction corners (modal click-through, mid-animation input, concurrent state). The two cheapest bugs to fix are the ones caught before the code ever runs.

### 4. Real-product verification (iron rule)
All-green static checks ≠ it works. Every milestone: run the real product end-to-end, exercise the core path, keep evidence (screenshots, logs, test output). Report evidence, not adjectives.

- **If the product can't be driven, make it drivable first.** Environment blocks real verification (headless browser throttles rAF, no display, async UI)? Don't downgrade to static checks — build a deterministic test hook *into the product* (step-the-clock / inject-input / introspect-state, e.g. a `window.__test` API), then simulate the full loop through it. Testability is a product feature; ship it.
- **Measure, don't eyeball.** Screenshots lie (JPEG, perception bias). When a visual looks wrong, compute the expected value (RGB after blending, px position) and sample-compare before "fixing" anything. A non-bug fixed is a bug added.
- **Verify the full loop after the last fix**, not just the step that failed — fixes shift behavior upstream and downstream.

### 5. Context hygiene (external memory)
`docs/SPEC.md` + `docs/PROGRESS.md` updated in real time, not batched. Segment long tasks: each segment restores from SPEC + PROGRESS only. Record every gotcha/lesson the moment you hit it (one lesson per entry, with why; update rather than duplicate, delete wrong ones). Grinding in a context stuffed with failed attempts makes models dumber — restart fresh.

### 6. Checkpoint autonomy
Background long tasks get a **watchdog** (output-file mtime). Organize resumable: any step dying loses at most one card. Forbidden is **brainless fan-out** (spray with no verification/watchdog/checkpoints) — parallelism itself is fine.

## Failure attribution ladder (before touching the fix)

When acceptance fails — or a fix "doesn't work" — attribute before you edit, cheapest layer first:

1. **The harness**: test drivers and acceptance scripts are code too. A too-conservative driver strategy or a wrong expected-value reads exactly like a product bug. Falsify the test before the tested.
2. **The deployment**: prove the new code is actually running — look for a behavior signature only the new version has (or stamp one), bust caches (`fetch(url, {cache:'reload'})`, restart, rebuild). "Fix had no effect" is, embarrassingly often, "fix never ran".
3. **The product**: only now debug. And fix the **class, not the instance** — restate the bug as a violated invariant and enforce the invariant ("every color's un-merged bucket count stays ≡ 0 mod 3"), instead of patching the one observed symptom. Then rerun the whole loop (see lever 4).

Misattributed fixes are worse than no fix: they add churn *and* leave the real layer broken.

## The Fable 5 habit set (any model, always)

1. **Ground every progress claim** in a tool result from this session; unverified means saying "unverified".
2. **Never end on a promise**: if your last paragraph is a plan / next-steps / "I'll now X" you could act on, act now. End only when done or blocked on user-only input.
3. **Lead with the outcome**; keep output short by selectivity, not compression.
4. **Pause only where the user is genuinely needed**: destructive/irreversible actions, real scope changes, user-only input.
5. **Assessment vs action**: when the user describes a problem or asks a question, deliver the assessment and stop; before state-changing commands, check the evidence supports that specific action.
6. **Give the reason, not only the request**, when delegating — intent travels with the card.
7. **Declare workflow deviations**: when the task's meta-intent overrides a standing default (e.g. "observe my execution" rules out delegating execution), say so in one line with the reason — never silently comply with the default, never silently deviate from it.

## Delegation policy (concurrency, model, escalation)

**Concurrency** — conservative by default: **≤5 concurrent**, inline-first, don't split when unsure. The throughput tier (dispatch readily, async, no fixed cap — field deployments 10-500+; subagents are one level deep) opens **only** when the user explicitly asks or the session model is Fable-class; state the honest cost: ~15x tokens + rate-limit risk. Never open it silently.

**Model routing (capability-matched)** — mirrors Anthropic's own practice (Opus-class lead + Sonnet-class subagents; Explore on Haiku; inherit when unsure):

| Card | Model | Effort |
|---|---|---|
| Orchestration, design, debugging, root-cause | session model | high/max |
| Verification, acceptance, adversarial refute | session model — **never weaker than the implementer** | max |
| Well-specified implementation (machine-checkable acceptance) | one tier down OK | high |
| Mechanical gather/format/search | cheap tier | low |

**Safety net — what makes downgrading safe:**
- Only downgrade cards whose acceptance is **machine-checkable**; vague or judgment-laden cards stay on the session model.
- Acceptance fails once → retry with the failure output; fails twice → escalate one tier, **capped at the session model** — the top of the ladder is pulling the card back inline, never a stronger model. fable-mode exists to get Fable-5-grade results *without* Fable 5; never spawn above the session model (`FABLE_ESCALATION=on` for genuine upward deferral).
- When unsure which row a card is, inherit the session model.

## Enforcement layer (hooks — mechanics in `hooks/README.md`)

Four hooks turn the most-shirked rules into hard blocks. Armed **per project** by a `.fable/` directory (searched upward, bounded at the git root); without it they pass through silently. Pressure applies **per round** via `.fable/LEDGER.md`:

```
- [ ] 1. card (machine-checkable acceptance)   <- open: guards enforce
- [x] 2. done -- evidence: pytest 21/21        <- [x] REQUIRES a substantive evidence note
- [~] 3. not this round -- deferred: reason
PAUSED: reason                                 <- a line anywhere: enforcement off
```

(`PAUSED` **must carry a reason** — a bare `PAUSED` is ignored, pausing has to
be attributable. Evidence notes must be substantive: `evidence: ok` counts as
missing.)

- **Spawn Guard** (PreToolUse Agent/Task/Workflow): blocks a detailed spawn while the ledger has no **open** cards — no ledger, and equally a ledger holding only a finished round's closed cards (design gate: new fan-out needs a live card) — and blocks any spawn requesting a **model stronger than the session's** (model ceiling — checked on the `model` param and `model:` literals in Workflow scripts; stays active even when paused, it protects quota, not workflow).
- **Fail-Streak Reminder** (PostToolUse Bash, advisory): every 3rd consecutive failing command injects the attribution ladder — stops grinding on the wrong layer mechanically, not by willpower.
- **Close Guard** (Stop): blocks ending the turn while open `- [ ]` items remain, **and** while any `- [x]` lacks an `-- evidence:` note (evidence-on-close: adjectives don't close cards).
- **Profile Injector** (SessionStart): injects tier + routing + habits, **sized to the ledger state** — full when a round is starting/active, minimal when idle, one line when paused.

**Wrap-up lint**: `python3 <skill-dir>/hooks/fable_lint.py <project_dir>` — machine-checks the discipline itself (SPEC source tags present, open cards name acceptance, closed cards carry evidence). Run it at step 7 of the execution template; findings are open work.

**Per-task granularity**: *active* (open cards) = full enforcement; *idle* (no/all-closed cards) = close guard quiet and small tasks flow freely, but a **detailed** fan-out still needs a live card first; *paused* (a `PAUSED: reason` line) = guards off except the ceiling. Write PAUSED only when the user steers to work unrelated to the round; remove it to resume. Small spawns (<1500 chars) and forks skip the design gate; everything fails open (a guard bug never bricks the session); loop-safe.

**For substantial work: after writing the SPEC, `mkdir .fable` + create `.fable/LEDGER.md` to get the mechanical backstop.**

## Execution-order template

```
1. Restate goal + scope (if unclear ask once; then no requirement rework)
2. docs/SPEC.md + .fable/LEDGER.md cards — the gate
3. Execute cards (fresh contexts; Delegation policy)
4. Per-card acceptance -> update PROGRESS.md
5. Milestone adversarial self-check (refute or N-approach review)
6. End-to-end real verification, leave evidence
7. Wrap: fable_lint clean, PROGRESS complete, lessons recorded, push if asked
```

## Red lines

- No code before the plan gate (unless the task is in the "don't use" list).
- No "should be fine" in place of an acceptance command's actual output.
- No grinding in a failed-attempt-stuffed context — restart fresh.
- Faithful reporting: failures are failures, skips are skips.
