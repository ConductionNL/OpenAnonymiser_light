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

### Entiteiten

Twee soorten entiteiten worden gedetecteerd.

#### 1. Pattern-based (rule-based)
Deze entiteiten worden herkend via vaste patronen (regex, checksums, format-herkenning):

| Entity Type | Omschrijving |
|-------------|--------------|
| BSN | Burgerservicenummer (11-proef) |
| CASE_NO | Zaaknummers (patroon: zaak XX/YYYYYY) |
| CREDIT_CARD | Creditcardnummers (Luhn-check) |
| DATE | Datums (NL-formaat: dd-mm-jjjj, dd/mm/yyyy, etc.) |
| DRIVERS_LICENSE | Rijbewijsnummers (patroonherkenning) |
| EMAIL | E-mailadressen |
| IBAN | IBAN-nummers (checksum-validatie) |
| ID_NO | ID-kaartnummers |
| IP_ADDRESS | IPv4-adressen |
| KVK_NUMBER | Kamer van Koophandel-nummers |
| LICENSE_PLATE | Nederlandse kentekens (RDW-formaat) |
| MAC_ADDRESS | MAC-adressen |
| PHONE_NUMBER | Telefoonnummers (NL-formaat) |
| POSTCODE | Nederlandse postcodes |
| VAT_NUMBER | BTW-nummers |
| SOCIAL_MEDIA | Social media handles (@username) |
| TIME | Tijdspatronen (HH:MM, uur) |

#### 2. Contextuele NER (Machine Learning)
Deze entiteiten vereisen contextuele tekstbegrip via ML-modellen:

| Entity Type | Omschrijving | GLiNER | spaCy |
|-------------|--------------|--------|-------|
| **LOCATION** | Plaatsen, straten, adressen, wijken | ✅ | ✅ |
| **NORP** | Nationaliteiten, religies, etniciteit, politieke groepen | ✅ | ✅ |
| **ORGANIZATION** | Bedrijven, instellingen, organisaties | ✅ | ✅ |
| **PERSON** | Persoonsnamen | ✅ | ✅ |

**Voor NER prestaties van GLiNER & spaCy zie `/benchmarks`.**

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
