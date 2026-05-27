#!/usr/bin/env bash
# Convenience script — equivalent to `jobber claude-install` but usable from a
# fresh checkout before installing the package.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$HOME/.claude/skills/jobber"
mkdir -p "$DEST_DIR"
cp "$HERE/SKILL.md" "$DEST_DIR/SKILL.md"
echo "Installed $DEST_DIR/SKILL.md"

SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  python3 - "$SETTINGS" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text() or "{}")
perms = data.setdefault("permissions", {})
allow = perms.setdefault("allow", [])
rule = "Bash(jobber:*)"
if rule not in allow:
    allow.append(rule)
    p.write_text(json.dumps(data, indent=2))
    print(f"Allowlisted {rule} in {p}")
else:
    print(f"Already allowlisted {rule}")
PY
else
  echo "(no $SETTINGS to update; will be created on first Claude Code run)"
fi
