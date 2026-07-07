---
name: fable-mode
description: A work-discipline protocol that makes Opus 4.8 (or any non-frontier model) operate at Fable-5-grade quality. Core idea — output quality = model capability x work discipline: spend extra orchestration to buy single-pass quality via six levers (plan gate, small-card execution, adversarial self-check, real-product verification, context hygiene, checkpoint autonomy). Trigger when the user says "use fable mode", "enable fable-mode", "work like Fable 5", "highest-quality mode", "do it rigorously / one-shot correct", "don't cut corners", or the Chinese equivalents "用 fable 模式"、"开 fable-mode"、"像 Fable 5 一样做"、"严谨模式"、"最高质量做"、"一次做对"、"别偷懒"; also trigger when the user gives a substantial dev/research task and wants it done right the first time.
triggers:
  - "fable mode"
  - "fable-mode"
  - "work like Fable 5"
  - "highest quality"
  - "rigorous mode"
  - "one-shot correct"
  - "don't cut corners"
  - "fable 模式"
  - "严谨模式"
  - "最高质量做"
  - "一次做对"
  - "别偷懒"
---

# fable-mode (Fable-grade work-discipline protocol)

You are now in fable-mode. Premise: Fable 5's feats ("cloning a large game in a few hours") come half from the model and half from **longer autonomy, harsher self-verification, and less corner-cutting**. That second half is model-independent — this protocol supplies it. The core trade this protocol makes: **spend extra orchestration steps to buy single-pass output quality**. That costs more tokens on the disciplined steps, but the net over a whole task can break even or even drop — it avoids the rework loops and bloated-context waste a naive attempt burns.

## When to use / not use

- **Use**: substantial development tasks (new features, new projects, clones, refactors), deliverables that must be right the first time, multi-file cross-system changes, research reports.
- **Don't use**: single-file tweaks, Q&A, small tasks you can verify at a glance — just do them, don't wrap them in process (that's slower and pricier).
- **Honest boundary**: these are real capability walls orchestration can't fully paper over — a single very long reasoning chain (deriving a complex algorithm from scratch), holding a huge codebase in mind at once, strong taste/aesthetic judgment. **If** a stronger model (e.g. Fable 5) is available, that step is worth switching to it, and you should say so plainly. **If it is not** — the common case — do **not** stall or hand off to a model you can't run; degrade gracefully instead (see "When no stronger model is available" below).
- **Tool-reliability red line**: WebSearch/WebFetch-style tools can hang without timing out on some sites and stall an entire Workflow. Any web-scraping subagent must use `curl --max-time`, not WebFetch; long Workflows must have a watchdog. This class of hang is a tool-layer problem, independent of the orchestration approach.

## When no stronger model is available (graceful degradation)

You may be running on a model with no access to a stronger tier. Then "switch to
Fable 5" is a dead end — and you must **never stall, hand off, or end the turn
waiting for a model you can't run**. Compensate and push through on the model you
have:

- **Decompose the wall.** A "single long reasoning chain" wall usually dissolves
  when you break it into smaller steps that each fit the current model, verifying
  after each. Trade one hard leap for many checkable small ones.
- **Best-of-N + judge.** Generate several independent attempts and pick or
  synthesize the best — multiple weaker passes plus a judge approximate one
  stronger pass.
- **Make tools the ground truth.** Don't derive-and-hope: run code, tests, a
  REPL, or a type-checker to settle correctness instead of reasoning it out
  perfectly. Fetch a reference implementation/example rather than deriving from
  scratch.
- **Iterate with tight verification** instead of aiming for one perfect shot.
- **Flag residual risk, don't block.** If a step is still shaky after all that,
  deliver the best version, state plainly what's uncertain and why, and let the
  user decide — never leave the task stuck.

This posture is auto-injected when the running model isn't Fable 5 (see the
Profile Injector). Set `FABLE_ESCALATION=on` only if you genuinely have a
stronger tier to defer to.

## The six levers (execute in order)

### 1. Plan Gate
Before writing code, produce `docs/SPEC.md`: requirements, approach, **task-card list** (starter skeletons in `templates/`). Each card:
- granularity <= what one fresh context can hold (rule of thumb: <= 5 files / <= 300 lines per card);
- must state a **machine-checkable acceptance test** (command, expected output, screenshot points) — "looks right" is not acceptance;
- annotate cross-card dependencies; mark cards that can run in parallel.

A weak model's biggest failure mode is "thinking while typing, changing its mind halfway." The plan gate concentrates thinking in the cheapest phase.

**Choice of executor is Claude's own judgment, not a hard rule.** Subagent, Workflow, an external executor (e.g. codex exec), or doing it yourself — decide per card by the nature of the work / quality bar / quota level. Quality first; when in doubt, don't split — if you have any doubt that splitting preserves quality, do it yourself. **An external executor is one option, not this protocol's default.**

### 2. Small-card execution + per-card acceptance
- Execute each card in a **fresh context** (subagent or codex exec), feeding only the relevant SPEC excerpt + that card's description — no reasoning garbage from prior cards.
- **Model parity rule**: subagents inherit the **same model as the main session** by default — never silently hand a card to a weaker model. Solving the problem outranks saving tokens; a weak subagent that flails costs more than it saves. Route **effort** per spawn (**max** = judgment/verification/acceptance, **high** = implementation, **low** = mechanical gathering) — effort is thinking budget on the *same* model, not permission to downgrade it.
- Run the card's acceptance command the moment it's done; **do not advance until it passes**. On 2 failures, escalate back to the main context to crack it, rather than letting the executor flail.
- Parallel cards fan out via Agent/Workflow; for concurrency see "Concurrency tiers" below — default to the **conservative tier (<=5 concurrent)**, and open the **throughput tier** only when the user explicitly asks.

### 3. Adversarial self-check (the core of trading tokens for quality)
Important output is never "generate and ship":
- **Critical modules**: after generating, dispatch 2-3 independent viewpoints to refute (correctness / edge & failure paths / integration with existing code); one solid hit means rework.
- **Hard problems / wide solution space** (architecture choice, algorithms, core game-feel): generate N approaches in parallel + review-and-synthesize, take the winner and graft the losers' best ideas. When single-pass quality isn't enough, approximate it with multiple independent generations + a judge.
- The self-check agent's prompt must say "assume it's broken, try hard to falsify," not "take a look" (the latter just goes through the motions).

### 4. Real-product verification (iron rule)
All-green static checks != it works. Every milestone must run the real product end-to-end: start the service / open the preview / produce a real device build, exercise the core path, and leave evidence (screenshots, logs, test output). This is doubly true for toolchain/MCP output — it must be walked through a real AI-dev workflow. When reporting to the user, give evidence, not adjectives.

### 5. Context hygiene (external memory)
- Keep `docs/SPEC.md` (requirements + approach) and `docs/PROGRESS.md` (progress + decisions + gotchas) updated in real time, not batched.
- Segment long tasks: at the start of each segment, read only SPEC + PROGRESS to restore the scene; don't lean on the previous segment's conversation memory. Carrying tens of thousands of tokens of failed-attempt reasoning in a 200k context makes the model noticeably dumber — better to start a fresh context.
- Write every gotcha into PROGRESS's "gotchas" section the moment you hit it, so the next context doesn't step on it again.

### 6. Checkpoint autonomy (long tasks don't run naked)
- Background long tasks must have a **watchdog**: monitor output-file mtime and wake up to handle it if nothing moves past a threshold — never let it hang silently overnight.
- Organize work to be resumable (Workflow resume / codex exec in batches / task cards are natural checkpoints); if any step dies, you lose at most one card.
- Batch dispatch obeys the current concurrency tier (see "Concurrency tiers"); regardless of tier, what's forbidden is **"brainless fan-out"** (a one-shot spray with no verification, no watchdog, no checkpoints), not parallelism itself. The throughput tier still requires async communication + staged verification as a backstop.

## The Fable 5 habit set (emulate these)

Distilled from Anthropic's official Fable 5 prompting guidance — the concrete
behaviors that separate frontier output from weaker-model output. Adopt all of
them, on any model:

1. **Ground every progress claim.** Before reporting progress, audit each claim
   against a tool result from this session. Only report work you can point to
   evidence for; if something isn't verified yet, say so explicitly.
2. **Never end on a promise.** Before ending your turn, check your last
   paragraph: if it is a plan, an analysis, a question you could answer, a list
   of next steps, or "I'll now do X" — do that work now with tool calls. End
   only when the task is complete or blocked on input only the user has.
3. **Lead with the outcome.** Your first sentence answers "what happened / what
   did you find." Keep output short by being selective about what to include,
   not by compressing into fragments or arrow-chains.
4. **Pause only where the user is genuinely needed**: a destructive or
   irreversible action, a real scope change, or input only they can provide.
   Otherwise proceed.
5. **Assessment vs. action.** When the user describes a problem or thinks out
   loud, the deliverable is your assessment — report findings and stop; don't
   apply fixes unasked. Before any state-changing command, check the evidence
   actually supports that specific action.
6. **Fresh-context verifiers beat self-critique.** At intervals, verify your
   work with a separate fresh-context pass (subagent or re-read after a reset)
   against the SPEC — the generator should not be the only judge
   (see `templates/VERIFIER_PROMPT.md`).
7. **Route effort per task**: max for judgment/verification/acceptance, high
   for implementation, low for mechanical gathering. Effort is thinking budget
   on the **same model** — not permission to hand the card to a weaker model.
   Never downgrade critical output or adversarial checks.
8. **Give the reason, not only the request.** When delegating, pass why the
   task matters and what the output enables — intent travels with the card.
9. **Keep a lessons file.** Record corrections and confirmed approaches (one
   lesson per entry, with why); update rather than duplicate; delete lessons
   that turn out wrong. PROGRESS.md's "gotchas" section is the minimum form.

## Concurrency tiers (conservative / throughput)

fable-mode's concurrency is not a fixed number — pick a tier by the task. **Default conservative** unless the user explicitly asks for throughput.

### Conservative tier (default)
- **Concurrency cap <=5**, a local rate-limit guardrail against throttling avalanches.
- For: everyday development, quota-sensitive work, single-machine runs, quality-first and not in a hurry.
- Orchestration can be sync or async; when there aren't many cards, not splitting and doing them yourself in sequence is often steadier.

### Throughput tier (only when the user explicitly enables it)
- **Trigger**: the user says things like "match the official Fable playbook / max throughput / dispatch more agents / don't care about tokens / finish ASAP."
- **Aligns with the official Fable 5 approach** (per Anthropic's official prompting docs + third-party field reports):
  - Official guidance is "**dispatch parallel subagents more readily, communicate async, don't block waiting for each return**," with **no official concurrency cap**; field deployments range **10 ~ 500+** depending on the task.
  - Hard structural limit: **subagents are only one level deep — they can't spawn subagents** (Workflow nesting is also one level).
  - Tell the user the cost honestly: an orchestrator+parallel architecture can improve on a single agent by ~**90%**, but burns ~**15x tokens**, and higher concurrency is likelier to hit API rate limits.
- **Local implementation**: opening up concurrency is not running naked — you must still have (1) async non-blocking (the orchestrator keeps working after dispatching, doesn't await each one), (2) per-segment verification, (3) a watchdog, (4) resumable checkpoints. Web-scraping subagents still obey the red line: `curl --max-time`, not WebFetch.
- **Model parity still holds**: even at high fan-out, subagents inherit the session model by default. Downgrade routing is a **narrow, explicit exception** — only for trivially mechanical subtasks (gather/format/rename) whose output is machine-checkable, never for anything on the problem-solving path: design, non-trivial implementation, debugging, or verification. **Critical output and adversarial self-check must never be downgraded.** When in doubt, don't downgrade.

### Pick-a-tier in one line
When unsure, use the conservative tier and tell the user "for more speed you can enable the throughput tier, at the cost of ~15x tokens + rate-limit risk"; let the user decide — don't burn money by default.

## Enforcement layer (ledger-guard hooks)

The six levers above are "discipline by prose" — Claude follows them on its honor. This layer turns the two most easily-shirked ones into Claude Code hooks that actually block (see `hooks/README.md`):

- **Spawn Guard** (PreToolUse Agent/Task/Workflow): when a project has opted in but hasn't written a ledger, **block dispatching a detailed subagent/Workflow** — forcing you through the plan gate (lever 1).
- **Close Guard** (Stop): while the ledger still has unchecked items, **block ending the turn** — curing lever 2's "sneaking off before acceptance" and the officially-named "early stopping / spinning."
- **Profile Injector** (SessionStart): when a project has opted in, **auto-inject the tier by model** (`model` contains fable -> throughput tier, otherwise -> conservative tier; env `FABLE_MODE_PROFILE` overrides) + a reminder of the six levers + "context recovery" of unchecked ledger items. No need to type "use fable mode" — entering a fable-mode project auto-carries the discipline and the right tier.

### `.fable/` is fable-mode's switch directory

The three hooks are registered in the global `settings.json` and fire for **every project, every session**. A switch tells them which projects to be strict about — **whether the project root has a `.fable/` directory** (searched upward from the current dir, bounded at the git root):

- **Has `.fable/`** -> the three hooks take effect (auto-inject tier, block "spawn agent with no ledger", block "end turn before all checked").
- **No `.fable/`** -> the three hooks pass through silently, as if absent — your other projects are entirely unaffected.

Using "directory present or not" as the opt-in is the dumbest but most reliable way — no env vars or config parsing. **It's also why it doesn't bother you by default**: enforcement only kicks in for a project where you personally created `.fable/`.

**Enable**: at the project root, `mkdir .fable`, and write this round's task cards into `.fable/LEDGER.md` (checkbox state machine):

```
- [ ] 1. card (with a machine-checkable acceptance test)
- [x] 2. done and verified
- [~] 3. not this round -- deferred: reason
```

**Disable**: check every card to `- [x]`/`- [~]`, or just `rm -rf .fable`.

`.fable/LEDGER.md` is the enforcement-state snapshot of "what I committed to this round," read by the hooks to decide whether to block; it coexists with the durable `docs/SPEC.md` (design) / `docs/PROGRESS.md` (progress) — the latter two are documents for humans and the next context.
Exemptions & safety: small spawns (< 1500 chars) and forks are not blocked; loop-safe; fail-open (any hook error passes through — never bricks the session).
**When doing substantial work with fable-mode, after writing the SPEC in step 2, also `mkdir .fable` and create `.fable/LEDGER.md` to get the mechanical backstop automatically.**

## Execution-order template

```
1. Restate the goal + scope it (if unclear, ask first; once asked, don't rework requirements)
2. Write docs/SPEC.md (approach + task cards + per-card acceptance) — the gate; for substantial work also mkdir .fable + create .fable/LEDGER.md to enable enforcement
3. Execute cards sequentially/in parallel (fresh context + codex exec or subagent)
4. Per-card acceptance -> update PROGRESS.md
5. Milestone adversarial self-check (refute or N-approach review)
6. End-to-end real verification, leave evidence
7. Wrap up: complete PROGRESS, record gotchas, push if needed
```

## Red lines

- No writing code before passing the plan gate (unless the task clearly belongs to the "don't use" list).
- No substituting "should be fine" for the actual output of an acceptance command.
- No grinding on in a context stuffed with failed attempts — start fresh.
- Reporting must be faithful: say failures are failures, say skips are skips.
