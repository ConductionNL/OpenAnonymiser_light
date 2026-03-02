#!/usr/bin/env bash
# Security scan hook — draait bandit na podman build of Python file edits
# Wordt aangeroepen door Claude Code PostToolUse hook met JSON op stdin

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")

PROJECT_DIR="/home/gongoeloe/CONDUCTION/OpenAnonymiser_light"
VENV_BANDIT="$PROJECT_DIR/.venv/bin/bandit"

# Alleen bij podman build of Write/Edit op Python bestanden
RUN_SCAN=false

if echo "$CMD" | grep -q "podman build"; then
  RUN_SCAN=true
fi

if [[ "$TOOL" == "Write" || "$TOOL" == "Edit" ]]; then
  FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")
  if echo "$FILE" | grep -q "\.py$"; then
    RUN_SCAN=true
  fi
fi

if [ "$RUN_SCAN" = false ]; then
  exit 0
fi

if [ ! -f "$VENV_BANDIT" ]; then
  echo "[SECURITY] bandit niet gevonden in .venv — skip scan"
  exit 0
fi

echo "[SECURITY] bandit scan op src/..."
cd "$PROJECT_DIR"
RESULT=$("$VENV_BANDIT" -r src/ -ll -q 2>&1 || true)

if echo "$RESULT" | grep -q "No issues identified"; then
  echo "[SECURITY] OK — geen issues gevonden"
elif [ -z "$RESULT" ]; then
  echo "[SECURITY] OK — geen issues gevonden"
else
  echo "[SECURITY] Bevindingen:"
  echo "$RESULT"
fi
