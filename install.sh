#!/usr/bin/env bash
# fable-mode installer — registers the four guard hooks into your Claude Code
# settings.json. Idempotent and safe to re-run. Requires python3 (stdlib only).
#
# It resolves its OWN directory, so the hook paths are correct no matter where
# you cloned the skill, and it honors CLAUDE_CONFIG_DIR (falling back to
# ~/.claude) so it works regardless of where your Claude config lives.
#
# Usage:
#   bash install.sh            # register hooks
#   bash install.sh --uninstall # remove fable-mode's hooks again
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CONFIG_DIR/settings.json"
MODE="install"
[ "${1:-}" = "--uninstall" ] && MODE="uninstall"

command -v python3 >/dev/null 2>&1 || { echo "error: python3 is required" >&2; exit 1; }
mkdir -p "$CONFIG_DIR"

python3 - "$SETTINGS" "$SKILL_DIR" "$MODE" <<'PY'
import json, os, sys

settings_path, skill_dir, mode = sys.argv[1], sys.argv[2], sys.argv[3]
hooks_dir = os.path.join(skill_dir, "hooks")

# event -> (matcher or None, script filename)
SPECS = [
    ("SessionStart", None,                  "fable_profile_inject.py"),
    ("PreToolUse",   "Agent|Task|Workflow", "fable_spawn_guard.py"),
    ("PostToolUse",  "Bash",                "fable_fail_streak.py"),
    ("PostToolUse",  "Bash",                "fable_evidence_log.py"),
    ("Stop",         None,                   "fable_close_guard.py"),
]
NAMES = {fname for _, _, fname in SPECS}

data = {}
if os.path.exists(settings_path):
    with open(settings_path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            sys.exit("error: %s is not valid JSON (%s); leaving it untouched" % (settings_path, e))

hooks = data.get("hooks", {})

def prune(entries):
    """Drop any hook group that references one of our scripts (any path)."""
    kept = []
    for group in entries:
        group["hooks"] = [h for h in group.get("hooks", [])
                          if not any(n in h.get("command", "") for n in NAMES)]
        if group.get("hooks"):
            kept.append(group)
    return kept

if mode == "uninstall":
    for event in list(hooks.keys()):
        hooks[event] = prune(hooks[event])
        if not hooks[event]:
            del hooks[event]
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
    print("fable-mode hooks removed from %s" % settings_path)
    sys.exit(0)

# install: prune our old entries first (handles moves/upgrades), then add
# fresh. Prune ONCE per event before appending — pruning inside the append
# loop would strip the groups just added for an earlier spec on the same
# event (two hooks share PostToolUse/Bash).
added = 0
for event in {e for e, _, _ in SPECS}:
    hooks[event] = prune(hooks.get(event, []))
for event, matcher, fname in SPECS:
    group = {"hooks": [{"type": "command",
                        "command": "python3 %s" % os.path.join(hooks_dir, fname)}]}
    if matcher:
        group["matcher"] = matcher
    hooks[event].append(group)
    added += 1

data["hooks"] = hooks
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
print("fable-mode: %d hooks registered in %s" % (added, settings_path))
print("            hook scripts: %s" % hooks_dir)
PY

if [ "$MODE" = "install" ]; then
  echo "Done. Hooks take effect from your NEXT Claude Code session (settings"
  echo "are read at session start) — restart or open a new session to arm them."
  echo "They stay inert until a project has a .fable/ directory."
fi
