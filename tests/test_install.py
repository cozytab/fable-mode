#!/usr/bin/env python3
"""Tests for install.sh: fresh install, idempotency, merge, re-point, uninstall,
and CLAUDE_CONFIG_DIR handling. Requires bash + python3."""
import json, os, shutil, subprocess, tempfile, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_SRC = os.path.join(REPO, "install.sh")
NAMES = ["fable_profile_inject.py", "fable_spawn_guard.py", "fable_close_guard.py"]
passed = failed = 0


def check(name, cond):
    global passed, failed
    print(("PASS" if cond else "FAIL"), name)
    passed += cond
    failed += (not cond)


def make_skill(root, sub="skills/fable-mode"):
    d = os.path.join(root, sub)
    os.makedirs(os.path.join(d, "hooks"))
    shutil.copy(INSTALL_SRC, d)
    for n in NAMES:
        open(os.path.join(d, "hooks", n), "w").write("# stub\n")
    return d


def run(skill_dir, cfg, *args):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=cfg)
    return subprocess.run(["bash", os.path.join(skill_dir, "install.sh"), *args],
                          capture_output=True, text=True, env=env)


def load(cfg):
    with open(os.path.join(cfg, "settings.json"), encoding="utf-8") as f:
        return json.load(f)


def cmds(d):
    return [h["command"] for e in d.get("hooks", {})
            for g in d["hooks"][e] for h in g.get("hooks", [])]


T = tempfile.mkdtemp(prefix="fbinstall_")
try:
    skill = make_skill(T)
    cfg = os.path.join(T, "config"); os.makedirs(cfg)

    # A. fresh install into an empty config dir
    r = run(skill, cfg)
    d = load(cfg)
    check("install/fresh-creates-3-events",
          r.returncode == 0 and set(d["hooks"]) == {"SessionStart", "PreToolUse", "Stop"})
    check("install/absolute-paths", all(skill in c for c in cmds(d) if "fable_" in c))
    check("install/matcher-on-pretooluse",
          d["hooks"]["PreToolUse"][0].get("matcher") == "Agent|Task|Workflow")

    # B. idempotent — second run must not duplicate
    run(skill, cfg)
    d = load(cfg)
    check("install/idempotent", all(len(d["hooks"][e]) == 1 for e in d["hooks"]))

    # C. merge — preserve unrelated config + a user's own hook
    with open(os.path.join(cfg, "settings.json"), "w") as f:
        json.dump({"permissions": {"allow": ["Read"]},
                   "hooks": {"PreToolUse": [{"matcher": "Bash",
                             "hooks": [{"type": "command", "command": "echo mine"}]}]}}, f)
    run(skill, cfg)
    d = load(cfg)
    check("install/preserves-permissions", d.get("permissions") == {"allow": ["Read"]})
    check("install/preserves-user-hook", any("echo mine" in c for c in cmds(d)))
    check("install/adds-alongside-user", len(d["hooks"]["PreToolUse"]) == 2)

    # D. re-point when the skill moves to a new location
    skill2 = make_skill(T, sub="other/fable-mode")
    run(skill2, cfg)
    d = load(cfg)
    fable_cmds = [c for c in cmds(d) if "fable_" in c]
    check("install/repoint-to-new-path", all("/other/" in c for c in fable_cmds))
    check("install/no-stale-old-path", not any("/skills/fable-mode/hooks" in c for c in fable_cmds))
    check("install/no-dup-after-move", len(d["hooks"]["SessionStart"]) == 1)

    # E. uninstall removes only ours
    run(skill2, cfg, "--uninstall")
    d = load(cfg)
    check("uninstall/removes-ours", not any("fable_" in c for c in cmds(d)))
    check("uninstall/keeps-user-hook", any("echo mine" in c for c in cmds(d)))

    # F. bad JSON is left untouched (fail-safe)
    with open(os.path.join(cfg, "settings.json"), "w") as f:
        f.write("{ not json")
    r = run(skill, cfg)
    check("install/bad-json-refused", r.returncode != 0
          and open(os.path.join(cfg, "settings.json")).read() == "{ not json")
finally:
    shutil.rmtree(T, ignore_errors=True)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
