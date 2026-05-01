#!/usr/bin/env bash
# Pre-push gate — snelle checks voordat een 'git push' uitgevoerd wordt.
# Aan te roepen vanuit:
#   - .git/hooks/pre-push   (git-native, stdin = push refs — wordt genegeerd)
#   - direct                bash scripts/pre-push.sh
#
# Wat draait (alleen statische checks — geen live API, geen baseline-flap):
#   1. uv lock --check        — pyproject.toml en uv.lock zijn in sync
#   2. bandit -r src/ -lll    — alleen HIGH severity blokkeert
#
# Exit 0 = continue push; non-zero = block.
#
# Bewust NIET in scope:
#   - pytest tests/        → vereist draaiende API; CI doet dat
#   - ruff check           → baseline-issues bestaan al, gate moet niet flap-en
#   - container builds     → CI doet dat
# Voor een gerichte ruff-fix: 'uvx ruff check src/ --fix' handmatig.

set -uo pipefail

# Find repo root from script location, niet vanuit pwd (zodat git-hook ook werkt
# wanneer git aanroept vanuit subdirectory).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR" || { echo "pre-push: cannot cd to $PROJECT_DIR" >&2; exit 1; }

# Activeer venv als die bestaat — bandit/pytest komen daar vandaan.
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

FAILED=()

echo "🔒 pre-push checks…" >&2

# 1. uv lock check
if command -v uv >/dev/null 2>&1; then
  if ! uv lock --check 2>&1 | tail -5 >&2; then
    FAILED+=("uv.lock out of sync — run 'uv lock'")
  fi
fi

# 2. Bandit — alleen HIGH severity blokkeert (medium baseline geaccepteerd).
if command -v bandit >/dev/null 2>&1; then
  if ! bandit -r src/ -lll -q >&2; then
    FAILED+=("bandit HIGH severity — fix in src/")
  fi
fi

if (( ${#FAILED[@]} > 0 )); then
  echo "" >&2
  echo "❌ pre-push BLOCKED:" >&2
  for f in "${FAILED[@]}"; do
    echo "  - $f" >&2
  done
  echo "" >&2
  echo "Fix de issues lokaal en push opnieuw. Bypass tijdelijk met 'git push --no-verify' (niet aanbevolen)." >&2
  exit 1
fi

echo "✅ pre-push checks passed" >&2
exit 0
