#!/usr/bin/env python3
import json, os, subprocess, tempfile, shutil, sys

INJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "fable_profile_inject.py")
passed = failed = 0
tmps = []

def proj(with_fable=False, ledger=None):
    d = tempfile.mkdtemp(prefix="fbinj_"); tmps.append(d)
    os.mkdir(os.path.join(d, ".git"))
    if with_fable:
        fd = os.path.join(d, ".fable"); os.mkdir(fd)
        if ledger is not None:
            open(os.path.join(fd, "LEDGER.md"), "w").write(ledger)
    return d

def run(payload, env=None):
    e = dict(os.environ); e.update(env or {})
    p = subprocess.run([sys.executable, INJ], input=json.dumps(payload),
                       capture_output=True, text=True, env=e)
    return p.returncode, p.stdout

def check(name, cond):
    global passed, failed
    print(("PASS" if cond else "FAIL"), name)
    if cond: passed += 1
    else: failed += 1

def ctx(out):
    try: return json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except Exception: return None

# 1. no .fable -> exit 0, empty stdout
d = proj(with_fable=False)
rc, out = run({"cwd": d, "model": "claude-fable-5", "hook_event_name": "SessionStart"})
check("inject/no-fable-silent", rc == 0 and out.strip() == "")

# 2. .fable + fable model -> throughput
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-fable-5"})
c = ctx(out)
check("inject/fable-model-throughput", rc == 0 and c and "THROUGHPUT" in c and "claude-fable-5" in c)

# 3. .fable + opus model -> conservative
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-opus-4-8"})
c = ctx(out)
check("inject/opus-model-conservative", rc == 0 and c and "CONSERVATIVE" in c)

# 4. .fable + NO model field -> conservative default
d = proj(with_fable=True)
rc, out = run({"cwd": d})
c = ctx(out)
check("inject/no-model-defaults-conservative", rc == 0 and c and "CONSERVATIVE" in c and "unknown" in c)

# 5. env override throughput on opus model
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-opus-4-8"}, env={"FABLE_MODE_PROFILE": "throughput"})
c = ctx(out)
check("inject/env-override-throughput", rc == 0 and c and "THROUGHPUT" in c)

# 6. env override conservative on fable model
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-fable-5"}, env={"FABLE_MODE_PROFILE": "conservative"})
c = ctx(out)
check("inject/env-override-conservative", rc == 0 and c and "CONSERVATIVE" in c)

# 7. context recovery: open ledger items surfaced
d = proj(with_fable=True, ledger="- [ ] 1. finish parser\n- [x] 2. done\n- [ ] 3. write docs\n")
rc, out = run({"cwd": d, "model": "claude-opus-4-8"})
c = ctx(out)
check("inject/context-recovery", rc == 0 and c and "Context recovery" in c and "finish parser" in c and "write docs" in c and "2 open item(s)" in c)

# 8. valid JSON envelope shape
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-fable-5"})
try:
    j = json.loads(out); ok = j["hookSpecificOutput"]["hookEventName"] == "SessionStart"
except Exception: ok = False
check("inject/valid-json-envelope", ok)

# 9. malformed stdin -> exit 0, no crash
p = subprocess.run([sys.executable, INJ], input="}{garbage", capture_output=True, text=True)
check("inject/malformed-failopen", p.returncode == 0)

# 10. non-Fable session gets the no-escalation / graceful-degradation posture
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-opus-4-8"})
c = ctx(out)
check("inject/conservative-no-escalation", rc == 0 and c and "do NOT defer" in c and "FABLE_ESCALATION" in c)

# 11. Fable/throughput session does NOT get the no-escalation line
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-fable-5"})
c = ctx(out)
check("inject/throughput-no-escalation-absent", rc == 0 and c and "do NOT defer" not in c)

# 12. FABLE_ESCALATION=on suppresses the no-escalation line even for opus
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-opus-4-8"}, env={"FABLE_ESCALATION": "on"})
c = ctx(out)
check("inject/escalation-on-suppresses", rc == 0 and c and "CONSERVATIVE" in c and "do NOT defer" not in c)

# 13. Fable-5 habits injected on conservative tier
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-opus-4-8"})
c = ctx(out)
check("inject/habits-conservative", rc == 0 and c and "Fable-5 habits" in c and "audit every progress claim" in c)

# 14. Fable-5 habits injected on throughput tier too (universal)
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-fable-5"})
c = ctx(out)
check("inject/habits-throughput", rc == 0 and c and "Fable-5 habits" in c)

# 15/16. model parity: both tiers say subagents inherit the session model
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-opus-4-8"})
c = ctx(out)
check("inject/model-parity-conservative", rc == 0 and c and "inherit this session's model" in c)
d = proj(with_fable=True)
rc, out = run({"cwd": d, "model": "claude-fable-5"})
c = ctx(out)
check("inject/model-parity-throughput", rc == 0 and c and "inherit this session's model" in c and "cheaper tiers" not in c)

for d in tmps: shutil.rmtree(d, ignore_errors=True)
print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
