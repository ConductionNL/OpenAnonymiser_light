#!/usr/bin/env bash
# Agent lifecycle hook — logt SubagentStop en TaskCompleted naar build.log
# + desktop notificatie als notify-send beschikbaar is

set -euo pipefail

INPUT=$(cat)
EVENT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('hook_event_name', d.get('event','unknown')))" 2>/dev/null || echo "unknown")
AGENT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent_type', d.get('type','')))" 2>/dev/null || echo "")

LOG_DIR="/home/gongoeloe/CONDUCTION/OpenAnonymiser_light/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

case "$EVENT" in
  SubagentStop)
    MSG="agent klaar: ${AGENT:-onbekend}"
    ;;
  TaskCompleted)
    MSG="taak voltooid"
    ;;
  *)
    exit 0
    ;;
esac

echo "[$TIMESTAMP] [AGENT] $MSG" >> "$LOG_DIR/build.log"

# Desktop notificatie (werkt op systemen met notify-send / dunst / libnotify)
if command -v notify-send &>/dev/null; then
  notify-send "Claude Code" "$MSG" --urgency=low --expire-time=4000 2>/dev/null || true
fi
