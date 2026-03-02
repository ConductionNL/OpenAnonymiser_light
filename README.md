# OpenAnonymiser Light

Slanke API voor detectie en anonimisering van privacygevoelige informatie (PII) in Nederlandse tekst. Gebaseerd op [Microsoft Presidio](https://github.com/microsoft/presidio) met SpaCy NER (`nl_core_news_md`) en Nederlandse pattern recognizers.

**Productie:** https://api.openanonymiser.commonground.nu/api/v1/docs
**Staging:** https://api.openanonymiser.accept.commonground.nu/api/v1/docs

## Quickstart

```bash
uv venv && uv sync
uv run api.py
```

Swagger UI: [http://localhost:8080/api/v1/docs](http://localhost:8080/api/v1/docs)

## Endpoints

| Endpoint | Beschrijving |
|----------|-------------|
| `GET /api/v1/health` | Liveness check |
| `POST /api/v1/analyze` | Detecteer PII — geeft entiteiten + posities terug |
| `POST /api/v1/anonymize` | Anonimiseer tekst — vervangt PII door placeholders |

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
| NER | SpaCy `nl_core_news_lg` (dev) / `nl_core_news_md` (container) |
| Patronen | Custom Dutch regex recognizers |
| Package manager | uv |
| Container | Docker / Podman |
| Deployment | Helm + ArgoCD |
