#!/usr/bin/env bash
# Build log hook — schrijft significante acties naar logs/build.log
# Wordt aangeroepen door Claude Code PostToolUse hook met JSON op stdin

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Filter: alleen log als het een significante actie is
KEYWORDS="uv sync|uv run|pytest|podman build|podman run|helm install|helm upgrade|helm template|bandit|openspec"
if ! echo "$CMD" | grep -qE "$KEYWORDS"; then
  exit 0
fi

# Bepaal type
if echo "$CMD" | grep -q "podman build"; then TYPE="BUILD"
elif echo "$CMD" | grep -q "pytest"; then TYPE="TEST"
elif echo "$CMD" | grep -q "uv run"; then TYPE="RUN"
elif echo "$CMD" | grep -q "uv sync"; then TYPE="SYNC"
elif echo "$CMD" | grep -q "helm"; then TYPE="HELM"
elif echo "$CMD" | grep -q "bandit"; then TYPE="SECURITY"
elif echo "$CMD" | grep -q "openspec"; then TYPE="OPENSPEC"
else TYPE="CMD"
fi

LOG_DIR="/home/gongoeloe/CONDUCTION/OpenAnonymiser_light/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SHORT_CMD=$(echo "$CMD" | head -c 120 | tr '\n' ' ')

echo "[$TIMESTAMP] [$TYPE] $SHORT_CMD" >> "$LOG_DIR/build.log"
