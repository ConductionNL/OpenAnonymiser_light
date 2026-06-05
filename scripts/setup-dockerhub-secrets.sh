#!/usr/bin/env bash
# setup-dockerhub-secrets.sh
#
# Interactieve helper om DOCKER_USERNAME + DOCKER_PASSWORD in GitHub Actions
# te zetten voor deze repo. Gebruikt voor het roteren van Docker Hub
# Service Account credentials zonder dat de waardes via copy-paste of
# shell-history lekken.
#
# Vereisten:
#   - gh CLI ingelogd (gh auth status)
#   - schrijfrechten op de repo (admin/maintain)
#   - Docker Hub access token van de SA (https://hub.docker.com/settings/security)
#
# Twee gebruiksmodi:
#
# 1. Met .env.dockerhub (handig voor herhaalde rotaties):
#      Maak <repo-root>/.env.dockerhub met:
#        DOCKERHUB_USERNAME=conductiondeploy-bot
#        DOCKERHUB_TOKEN=dckr_pat_...
#      Daarna: bash scripts/setup-dockerhub-secrets.sh
#      (.env.dockerhub staat in .gitignore — checkt nooit in)
#
# 2. Zonder file → interactieve prompt (token wordt verborgen ingelezen).

set -euo pipefail

REPO="${REPO:-ConductionNL/OpenAnonymiser_light}"

# Pre-flight: gh aanwezig + ingelogd?
if ! command -v gh >/dev/null 2>&1; then
  echo "❌ gh CLI niet gevonden. Installeer via: https://cli.github.com/" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "❌ gh niet ingelogd. Run: gh auth login" >&2
  exit 1
fi

echo "🔐 Setup Docker Hub credentials voor $REPO"
echo

# Find repo root from script locatie zodat .env.dockerhub vindbaar is ongeacht cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env.dockerhub"

USERNAME=""
TOKEN=""

# Modus 1: lees .env.dockerhub als die bestaat
if [[ -f "$ENV_FILE" ]]; then
  echo "📁 Gebruik credentials uit $ENV_FILE"
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
  USERNAME="${DOCKERHUB_USERNAME:-}"
  TOKEN="${DOCKERHUB_TOKEN:-}"
  if [[ -z "$USERNAME" || -z "$TOKEN" ]]; then
    echo "❌ $ENV_FILE mist DOCKERHUB_USERNAME of DOCKERHUB_TOKEN." >&2
    exit 1
  fi
fi

# Modus 2: prompt-fallback als geen file
if [[ -z "$USERNAME" ]]; then
  read -rp "Docker Hub SA-username [conductiondeploy-bot]: " USERNAME
  USERNAME="${USERNAME:-conductiondeploy-bot}"
fi

if [[ -z "$TOKEN" ]]; then
  echo "Plak het Docker Hub access token (input wordt verborgen):"
  read -rsp "  token> " TOKEN
  echo
fi

if [[ -z "$USERNAME" || -z "$TOKEN" ]]; then
  echo "❌ Username en token mogen niet leeg zijn." >&2
  exit 1
fi

# Schrijven naar GitHub Secrets
echo
echo "→ DOCKER_USERNAME setten..."
gh secret set DOCKER_USERNAME --repo "$REPO" --body "$USERNAME"
echo "→ DOCKER_PASSWORD setten..."
gh secret set DOCKER_PASSWORD --repo "$REPO" --body "$TOKEN"

# Variabelen leegmaken (best-effort; bash houdt geen secrets in memory na exit)
unset TOKEN USERNAME

echo
echo "✅ Klaar. Verifieer met:"
echo "   gh secret list --repo $REPO"
echo
echo "Trigger CI opnieuw met:"
echo "   gh workflow run docker-build.yml --ref development --repo $REPO"
