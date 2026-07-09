#!/usr/bin/env python3
import json, os, subprocess, tempfile, shutil, sys

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks")
SPAWN = os.path.join(HOOKS, "fable_spawn_guard.py")
CLOSE = os.path.join(HOOKS, "fable_close_guard.py")

passed = failed = 0
def check(name, got, want):
    global passed, failed
    ok = got == want
    print(("PASS" if ok else "FAIL"), name, "exit=%s want=%s" % (got, want))
    if ok: passed += 1
    else: failed += 1

def run(script, payload):
    p = subprocess.run([sys.executable, script], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode

def mkproj(with_fable=False, ledger=None, git=False):
    d = tempfile.mkdtemp(prefix="fbtest_")
    if git: os.mkdir(os.path.join(d, ".git"))
    if with_fable:
        fd = os.path.join(d, ".fable"); os.mkdir(fd)
        if ledger is not None:
            with open(os.path.join(fd, "LEDGER.md"), "w") as f: f.write(ledger)
    return d

BIG = "x" * 2000
SMALL = "y" * 100
tmps = []
def proj(**kw):
    d = mkproj(**kw); tmps.append(d); return d

# ---- Spawn guard ----
# 1. no .fable -> allow even with big payload
d = proj(git=True)
check("spawn/no-fable-dir", run(SPAWN, {"cwd": d, "tool_name": "Agent",
      "tool_input": {"prompt": BIG}}), 0)

# 2. .fable, no ledger, big payload -> BLOCK
d = proj(with_fable=True, git=True)
check("spawn/optin-no-ledger-big", run(SPAWN, {"cwd": d, "tool_name": "Agent",
      "tool_input": {"prompt": BIG}}), 2)

# 3. .fable, ledger with cards, big payload -> allow
d = proj(with_fable=True, git=True, ledger="- [ ] 1. do a thing\n- [x] 2. done\n")
check("spawn/optin-with-ledger-big", run(SPAWN, {"cwd": d, "tool_name": "Workflow",
      "tool_input": {"script": BIG}}), 0)

# 4. .fable, no ledger, SMALL payload -> allow (exempt)
d = proj(with_fable=True, git=True)
check("spawn/optin-no-ledger-small", run(SPAWN, {"cwd": d, "tool_name": "Agent",
      "tool_input": {"prompt": SMALL}}), 0)

# 5. .fable, no ledger, big payload, FORK -> allow (exempt)
d = proj(with_fable=True, git=True)
check("spawn/fork-exempt", run(SPAWN, {"cwd": d, "tool_name": "Agent",
      "tool_input": {"prompt": BIG, "subagent_type": "fork"}}), 0)

# 6. malformed stdin -> fail-open allow (cwd isolated: the hook falls back to
# process cwd, which must not accidentally sit inside a .fable project)
p = subprocess.run([sys.executable, SPAWN], input="not json{{",
                   capture_output=True, text=True, cwd=proj(git=True))
check("spawn/malformed-failopen", p.returncode, 0)

# 7. git-root boundary: .fable is ABOVE a git root -> should NOT arm inner proj
outer = tempfile.mkdtemp(prefix="fbouter_"); tmps.append(outer)
os.mkdir(os.path.join(outer, ".fable"))
inner = os.path.join(outer, "repo"); os.mkdir(inner); os.mkdir(os.path.join(inner, ".git"))
check("spawn/git-boundary-stops", run(SPAWN, {"cwd": inner, "tool_name": "Agent",
      "tool_input": {"prompt": BIG}}), 0)

# ---- Close guard ----
# 1. no .fable -> allow stop
d = proj(git=True)
check("close/no-fable", run(CLOSE, {"cwd": d}), 0)

# 2. ledger with open item -> BLOCK stop
d = proj(with_fable=True, git=True, ledger="- [ ] 1. unfinished\n- [x] 2. done\n")
check("close/open-item-block", run(CLOSE, {"cwd": d}), 2)

# 3. ledger all closed WITH evidence -> allow
d = proj(with_fable=True, git=True,
         ledger="- [x] 1. done -- evidence: pytest 21/21\n"
                "- [~] 2. skip -- deferred: n/a\n")
check("close/all-closed-allow", run(CLOSE, {"cwd": d}), 0)

# 4. open item BUT stop_hook_active -> allow (loop safety)
d = proj(with_fable=True, git=True, ledger="- [ ] 1. unfinished\n")
check("close/loop-safety", run(CLOSE, {"cwd": d, "stop_hook_active": True}), 0)

# 5. .fable but no ledger file -> allow
d = proj(with_fable=True, git=True)
check("close/no-ledger-file", run(CLOSE, {"cwd": d}), 0)

# 6. malformed -> allow (cwd isolated, same reason as spawn test 6)
p = subprocess.run([sys.executable, CLOSE], input="}{bad", capture_output=True,
                   text=True, cwd=proj(git=True))
check("close/malformed-failopen", p.returncode, 0)

# ---- Evidence-on-close (close guard) ----
# 1. all closed but a [x] lacks evidence -> BLOCK
d = proj(with_fable=True, git=True, ledger="- [x] 1. done\n")
check("evidence/missing-blocks", run(CLOSE, {"cwd": d}), 2)

# 2. Chinese marker accepted
d = proj(with_fable=True, git=True, ledger="- [x] 1. 完成 —— 证据: 截图 x.png\n")
check("evidence/zh-marker-allows", run(CLOSE, {"cwd": d}), 0)

# 2b. legacy `verified:` marker accepted (template compatibility)
d = proj(with_fable=True, git=True, ledger="- [x] 1. done — verified: pytest 12 passed\n")
check("evidence/verified-marker-allows", run(CLOSE, {"cwd": d}), 0)

# 3. open items take precedence (block message is about the open card)
d = proj(with_fable=True, git=True, ledger="- [ ] 1. open\n- [x] 2. done\n")
check("evidence/open-still-blocks", run(CLOSE, {"cwd": d}), 2)

# 4. PAUSED disables evidence enforcement too
d = proj(with_fable=True, git=True, ledger="- [x] 1. done\nPAUSED: side work\n")
check("evidence/paused-allows", run(CLOSE, {"cwd": d}), 0)

# 5. loop safety still applies
d = proj(with_fable=True, git=True, ledger="- [x] 1. done\n")
check("evidence/loop-safety", run(CLOSE, {"cwd": d, "stop_hook_active": True}), 0)

# ---- Fail-streak reminder (PostToolUse Bash) ----
STREAK = os.path.join(HOOKS, "fable_fail_streak.py")

def run_streak(payload):
    p = subprocess.run([sys.executable, STREAK], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stdout

FAIL_RESP = {"stdout": "", "stderr": "boom", "exitCode": 1}
OK_RESP = {"stdout": "ok", "stderr": "", "exitCode": 0}

# unique per run: the streak file persists in tempdir, stale counts would skew
import time
RUN_TAG = "%d" % (time.time() * 1000)

# 1. three consecutive failures -> advisory context on the 3rd, exit 0 always
d = proj(with_fable=True, git=True, ledger="- [ ] 1. card\n")
sid = "fbtest-streak-1-" + RUN_TAG
outs = [run_streak({"cwd": d, "session_id": sid, "tool_name": "Bash",
                    "tool_response": FAIL_RESP}) for _ in range(3)]
check("streak/all-exit-0", all(rc == 0 for rc, _ in outs), True)
check("streak/quiet-before-3", ("additionalContext" not in outs[0][1]
                                and "additionalContext" not in outs[1][1]), True)
check("streak/reminds-at-3", "attribution ladder" in outs[2][1], True)

# 2. success resets the streak
run_streak({"cwd": d, "session_id": sid, "tool_name": "Bash", "tool_response": OK_RESP})
rc, out = run_streak({"cwd": d, "session_id": sid, "tool_name": "Bash",
                      "tool_response": FAIL_RESP})
check("streak/success-resets", "additionalContext" not in out, True)

# 3. not opted in -> inert even on failures
d2 = proj(git=True)
sid2 = "fbtest-streak-2-" + RUN_TAG
outs = [run_streak({"cwd": d2, "session_id": sid2, "tool_name": "Bash",
                    "tool_response": FAIL_RESP}) for _ in range(4)]
check("streak/no-fable-inert", all("additionalContext" not in o for _, o in outs), True)

# 4. PAUSED (with a reason — bare PAUSED is ignored by design) -> off
d3 = proj(with_fable=True, git=True, ledger="- [ ] 1. c\nPAUSED: side work\n")
sid3 = "fbtest-streak-3-" + RUN_TAG
outs = [run_streak({"cwd": d3, "session_id": sid3, "tool_name": "Bash",
                    "tool_response": FAIL_RESP}) for _ in range(4)]
check("streak/paused-off", all("additionalContext" not in o for _, o in outs), True)

# ---- fable_lint ----
LINT = os.path.join(HOOKS, "fable_lint.py")

def run_lint(d):
    p = subprocess.run([sys.executable, LINT, d], capture_output=True, text=True)
    return p.returncode, p.stdout

# 1. clean project -> exit 0
d = proj(with_fable=True, git=True,
         ledger="- [ ] 1. build x -- acceptance: `pytest -q`\n"
                "- [x] 2. done -- evidence: 21/21 green\n")
os.makedirs(os.path.join(d, "docs"))
with open(os.path.join(d, "docs", "SPEC.md"), "w") as f:
    f.write("# spec\n- rate 1000/s [measured]\n")
rc, out = run_lint(d)
check("lint/clean-exit-0", rc, 0)

# 2. violations (no tags, no acceptance hint, no evidence) -> exit 1, 3 findings
d = proj(with_fable=True, git=True,
         ledger="- [ ] 1. vague card\n- [x] 2. done\n")
os.makedirs(os.path.join(d, "docs"))
with open(os.path.join(d, "docs", "SPEC.md"), "w") as f:
    f.write("# spec with no tags\n")
rc, out = run_lint(d)
check("lint/violations-exit-1", rc, 1)
check("lint/finds-all-three", out.count("FINDING") == 3, True)

# 3. not a fable project -> exit 0 with note
rc, out = run_lint(proj(git=True))
check("lint/non-project-exit-0", rc, 0)

# ---- Model ceiling (spawn guard + injector session cache) ----
INJ = os.path.join(HOOKS, "fable_profile_inject.py")

def run_env(script, payload, env=None):
    e = dict(os.environ); e.update(env or {})
    p = subprocess.run([sys.executable, script], input=json.dumps(payload),
                       capture_output=True, text=True, env=e)
    return p.returncode

def seed_session(sid, model):
    """SessionStart caches {session_id -> model} for the guard."""
    subprocess.run([sys.executable, INJ], input=json.dumps(
        {"cwd": proj(git=True), "session_id": sid, "model": model}),
        capture_output=True, text=True)

LEDGER_OK = "- [ ] 1. a card\n"
seed_session("fbtest-ceil-opus", "claude-opus-4-8")

# 1. opus session + spawn model=fable -> BLOCK (even small prompt, ledger present)
d = proj(with_fable=True, git=True, ledger=LEDGER_OK)
check("ceiling/fable-blocked", run_env(SPAWN, {"cwd": d, "session_id": "fbtest-ceil-opus",
      "tool_name": "Agent", "tool_input": {"prompt": SMALL, "model": "fable"}}), 2)

# 2. downgrade (sonnet) -> allow
d = proj(with_fable=True, git=True, ledger=LEDGER_OK)
check("ceiling/sonnet-allowed", run_env(SPAWN, {"cwd": d, "session_id": "fbtest-ceil-opus",
      "tool_name": "Agent", "tool_input": {"prompt": SMALL, "model": "sonnet"}}), 0)

# 3. no model param (inherit) -> allow
d = proj(with_fable=True, git=True, ledger=LEDGER_OK)
check("ceiling/inherit-allowed", run_env(SPAWN, {"cwd": d, "session_id": "fbtest-ceil-opus",
      "tool_name": "Agent", "tool_input": {"prompt": SMALL}}), 0)

# 4. FABLE_ESCALATION=on -> allow upward
d = proj(with_fable=True, git=True, ledger=LEDGER_OK)
check("ceiling/escalation-on-allows", run_env(SPAWN, {"cwd": d, "session_id": "fbtest-ceil-opus",
      "tool_name": "Agent", "tool_input": {"prompt": SMALL, "model": "fable"}},
      env={"FABLE_ESCALATION": "on"}), 0)

# 5. unknown session model -> fail-open allow
d = proj(with_fable=True, git=True, ledger=LEDGER_OK)
check("ceiling/unknown-session-failopen", run_env(SPAWN, {"cwd": d,
      "session_id": "fbtest-ceil-nocache", "tool_name": "Agent",
      "tool_input": {"prompt": SMALL, "model": "fable"}}), 0)

# 6. Workflow script with model: 'fable' literal -> BLOCK
d = proj(with_fable=True, git=True, ledger=LEDGER_OK)
check("ceiling/workflow-script-blocked", run_env(SPAWN, {"cwd": d,
      "session_id": "fbtest-ceil-opus", "tool_name": "Workflow",
      "tool_input": {"script": "await agent('x', {model: 'fable'})"}}), 2)

# 7. REGRESSION: prose mentioning 'fable-mode' (no model key) must NOT block
d = proj(with_fable=True, git=True, ledger=LEDGER_OK)
check("ceiling/no-false-positive-on-prose", run_env(SPAWN, {"cwd": d,
      "session_id": "fbtest-ceil-opus", "tool_name": "Workflow",
      "tool_input": {"script": "// follow the fable-mode protocol strictly"}}), 0)

# 8. no .fable dir -> ceiling inert even for model=fable
d = proj(git=True)
check("ceiling/no-fable-inert", run_env(SPAWN, {"cwd": d, "session_id": "fbtest-ceil-opus",
      "tool_name": "Agent", "tool_input": {"prompt": SMALL, "model": "fable"}}), 0)

# ---- PAUSED semantics ----
# a. open card + PAUSED -> close guard allows stop
d = proj(with_fable=True, git=True, ledger="- [ ] 1. big card\nPAUSED: side work\n")
check("paused/close-allows", run(CLOSE, {"cwd": d}), 0)

# b. PAUSED with no cards -> spawn design gate off (big payload allowed)
d = proj(with_fable=True, git=True, ledger="PAUSED: side work\n")
check("paused/spawn-gate-off", run(SPAWN, {"cwd": d, "tool_name": "Agent",
      "tool_input": {"prompt": BIG}}), 0)

# c. PAUSED does NOT disable the model ceiling (quota protection stays)
d = proj(with_fable=True, git=True, ledger="- [ ] 1. card\nPAUSED: side work\n")
check("paused/ceiling-still-blocks", run_env(SPAWN, {"cwd": d,
      "session_id": "fbtest-ceil-opus", "tool_name": "Agent",
      "tool_input": {"prompt": SMALL, "model": "fable"}}), 2)

# ---- Rigor floor (2026-07-08) ----
# 1. stale closed cards must NOT unlock new fan-out: all-closed + big -> BLOCK
d = proj(with_fable=True, git=True,
         ledger="- [x] 1. done -- evidence: pytest 21/21\n")
check("floor/all-closed-big-spawn-blocked", run(SPAWN, {"cwd": d,
      "tool_name": "Agent", "tool_input": {"prompt": BIG}}), 2)

# 2. bare PAUSED (no reason) is ignored -> close guard still blocks open items
d = proj(with_fable=True, git=True, ledger="- [ ] 1. open card\nPAUSED\n")
check("floor/bare-paused-ignored-close", run(CLOSE, {"cwd": d}), 2)

# 3. bare PAUSED is ignored by the spawn design gate too (no open cards)
d = proj(with_fable=True, git=True, ledger="PAUSED:\n")
check("floor/bare-paused-ignored-spawn", run(SPAWN, {"cwd": d,
      "tool_name": "Agent", "tool_input": {"prompt": BIG}}), 2)

# 4. reasoned PAUSED still works (regression)
d = proj(with_fable=True, git=True, ledger="- [ ] 1. open\nPAUSED: user side-quest\n")
check("floor/reasoned-paused-still-works", run(CLOSE, {"cwd": d}), 0)

# 5. hollow evidence ("evidence: ok") counts as missing -> BLOCK
d = proj(with_fable=True, git=True, ledger="- [x] 1. done -- evidence: ok\n")
check("floor/hollow-evidence-blocks", run(CLOSE, {"cwd": d}), 2)

# 6. substantive evidence passes (regression)
d = proj(with_fable=True, git=True,
         ledger="- [x] 1. done -- evidence: 40/40 tests green\n")
check("floor/substantive-evidence-allows", run(CLOSE, {"cwd": d}), 0)

for d in tmps:
    shutil.rmtree(d, ignore_errors=True)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
