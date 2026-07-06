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

# 6. malformed stdin -> fail-open allow
p = subprocess.run([sys.executable, SPAWN], input="not json{{",
                   capture_output=True, text=True)
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

# 3. ledger all closed -> allow
d = proj(with_fable=True, git=True, ledger="- [x] 1. done\n- [~] 2. skip -- deferred: n/a\n")
check("close/all-closed-allow", run(CLOSE, {"cwd": d}), 0)

# 4. open item BUT stop_hook_active -> allow (loop safety)
d = proj(with_fable=True, git=True, ledger="- [ ] 1. unfinished\n")
check("close/loop-safety", run(CLOSE, {"cwd": d, "stop_hook_active": True}), 0)

# 5. .fable but no ledger file -> allow
d = proj(with_fable=True, git=True)
check("close/no-ledger-file", run(CLOSE, {"cwd": d}), 0)

# 6. malformed -> allow
p = subprocess.run([sys.executable, CLOSE], input="}{bad", capture_output=True, text=True)
check("close/malformed-failopen", p.returncode, 0)

for d in tmps:
    shutil.rmtree(d, ignore_errors=True)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
