# OpenAnonymiser Light

Slanke API voor detectie en anonimisering van privacygevoelige informatie (PII) in Nederlandse tekst. Gebaseerd op [Microsoft Presidio](https://github.com/microsoft/presidio) met SpaCy NER (`nl_core_news_lg`) en Nederlandse pattern recognizers.

**Productie:** https://api.openanonymiser.commonground.nu/api/v1/docs
**Staging:** https://api.openanonymiser.accept.commonground.nu/api/v1/docs

## Quickstart

```bash
uv venv && uv sync                 # base = classic-flavor (geen GLiNER)
uv run api.py
```

GPU-flavor lokaal testen (extra deps: GLiNER, torch, CUDA):

```bash
uv sync --extra gpu
PLUGINS_CONFIG=src/api/plugins.gpu.yaml uv run api.py
```

Swagger UI: [http://localhost:8080/api/v1/docs](http://localhost:8080/api/v1/docs)

## Flavors

OpenAnonymiser bouwt twee container-flavors uit deze branch — selectie via Dockerfile + `PLUGINS_CONFIG` env-var. Zie [`docs/architecture/flavors.md`](docs/architecture/flavors.md) voor de volledige uitleg.

| Flavor | Engines | Use case | GPU vereist? |
|---|---|---|---|
| `classic` | spaCy + Dutch regex | sidecar, Nextcloud-app, on-prem appliance | nee |
| `gpu` | spaCy + GLiNER + regex | managed SaaS met GPU-pool | ja (productie) |
| `contextual` | gpu + verifier (BSN/ID) | managed SaaS met externe LLM/transformer | ja (productie) — niet geïmplementeerd |

```bash
# classic build (lichtgewicht, CPU)
docker build -f Dockerfile.classic -t openanonymiser-light:dev-classic .

# gpu build (~3GB image — bevat GLiNER + mdeberta)
docker build -f Dockerfile.gpu -t openanonymiser-light:dev-gpu .
```

CI bouwt beide flavors per push naar `development`/`staging`/`main` met tags `:{tier}-{flavor}`. Default-aliases: `:latest` = classic-main, `:acc` = classic-acc, `:dev` = gpu-development.

## Endpoints

| Endpoint | Beschrijving |
|----------|-------------|
| `GET /api/v1/health` | Liveness check |
| `POST /api/v1/analyze` | Detecteer PII — geeft entiteiten + posities terug |
| `POST /api/v1/anonymize` | Anonimiseer tekst — vervangt PII door placeholders |

## Pre-push gate (optioneel)

Snelle checks vóór `git push` — uv-lock-sync + bandit HIGH severity. Geen API of containers nodig, draait in <1 s.

```bash
# Eenmalig installeren als git pre-push hook
ln -sf ../../scripts/pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

Bypass tijdelijk met `git push --no-verify`. Volledige test-suite + container builds blijven CI's verantwoordelijkheid.

## Documentatie

- [01 Getting Started](docs/01-getting-started.md) — installatie, eerste verzoek, entiteittypes
- [02 API Reference](docs/02-api-reference.md) — alle endpoints met curl-voorbeelden
- [03 Configuration](docs/03-configuration.md) — env vars, modellen, pattern recognizers
- [04 Deployment](docs/04-deployment.md) — container, Kubernetes/Helm, CI/CD
- [Contributing](CONTRIBUTING.md) — branching, code standards, tooling

## Stack

| Component | Technologie |
|-----------|------------|
| Framework | FastAPI + Presidio |
| NER | SpaCy `nl_core_news_lg` (overal — lokaal, container, K8s) |
| Patronen | Custom Dutch regex recognizers |
| Package manager | uv |
| Container | Docker |
| Deployment | Helm + ArgoCD |
