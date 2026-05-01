# OpenAnonymiser – Claude instructies

## Project context

Slanke presidio + SpaCy NER API voor PII-detectie in Nederlandse tekst.
- **API**: `src/api/` — FastAPI, presidio, SpaCy `nl_core_news_lg` (overal — lokaal, container, K8s)
- **Patronen**: `src/api/utils/patterns.py` — regex-based recognizers
- **Tests**: `tests/` — httpx/requests tegen draaiende API
- **Deployment**: `Dockerfile.classic` / `Dockerfile.gpu` (per flavor) + kustomize onder `k8s/`

## Vaste gedragsregels

### 1. Altijd refactoren
- Verwijder dode code, ongebruikte imports en bestanden zonder te vragen.
- Als iets niet gebruikt wordt: weg ermee. Geen commentaar-blokken voor verwijderde code.
- Voorkeur voor kleine, gerichte wijzigingen boven grote rewrites.

### 2. Lokaal = vrij handelen
- Lokale acties (testen, draaien, bouwen, lint) uitvoeren zonder bevestiging te vragen.
- Bevestiging is **alleen** nodig voor: `git push`, `docker push`, `helm install/upgrade`, `kubectl apply/delete`.

### 3. Documentatie bijhouden
- Als een endpoint, configuratie of gedrag verandert: update README.md en `.env.example` mee.
- Houd de openspec change-artifacts (proposal/design/tasks) actueel bij wijzigingen.

### 4. Security
- Na elke container build: voer `bandit -r src/ -ll -q` uit en rapporteer bevindingen.
- Geen hardcoded secrets. CRYPTO_KEY, wachtwoorden altijd via env-vars.
- Bekijk Dockerfile op: root-user, world-writable mounts, onnodige packages.

### 5. Build log
- Elke significante actie (build, test-run, sync) wordt gelogd naar `logs/build.log`.
- Format: `[DATUM TIJD] [TYPE] commando → resultaat`

## Deployment straat

```
uv run api.py                    →  lokaal (port 8080)
docker build                     →  image bouwen
docker run                       →  container smoke-test
helm template                    →  dry-run validatie
helm install/upgrade             →  VRAAG EERST ← deploy-actie
```

## Veelgebruikte commando's

```bash
# Lokaal starten
uv run api.py --host 0.0.0.0 --port 8080

# Tests draaien
source .venv/bin/activate && pytest tests/ -q

# Container bouwen
docker build -t openanonymiser-light:latest .

# Security scan
source .venv/bin/activate && bandit -r src/ -ll -q

# Helm dry-run
helm template openanonymiser ./charts/openanonymiser

# openspec workflow
openspec list
openspec status --change <naam>
```

## SpaCy model

`nl_core_news_lg` overal — lokaal venv, Docker image, K8s. Wordt door
`uv sync` geïnstalleerd vanuit `pyproject.toml` (hard dep). Override via
`DEFAULT_SPACY_MODEL=...` env-var alleen voor experimenten; productie-pad
is altijd lg.
