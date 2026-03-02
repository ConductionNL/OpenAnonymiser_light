# Configuration

## Omgevingsvariabelen

Kopieer `.env.example` naar `.env` voor lokale development:

```bash
cp .env.example .env
```

| Variabele | Standaard | Beschrijving |
|-----------|-----------|--------------|
| `DEBUG` | `true` | Debug-modus (zet `false` in productie) |
| `UVICORN_SERVER_MODE` | `development` | `development` \| `staging` \| `production` |
| `DEFAULT_LANGUAGE` | `nl` | Taalcode voor PII-detectie |
| `DEFAULT_NLP_ENGINE` | `spacy` | NLP engine: alleen `spacy` |
| `DEFAULT_SPACY_MODEL` | `nl_core_news_md` | SpaCy-model naam |
| `LOG_DIR` | `logs` | Map voor applicatielogs |

## SpaCy-modellen

| Context | Model | Hoe geladen |
|---------|-------|-------------|
| Lokale dev (venv) | `nl_core_news_lg` | Via `uv sync` (pyproject.toml) |
| Container / productie | `nl_core_news_md` | Baked in via Dockerfile |

De modelkeuze wordt bepaald door `DEFAULT_SPACY_MODEL`. De twee modellen zijn functioneel equivalent voor NER; `_lg` is groter (hogere recall), `_md` is compacter (geschikt voor containers).

## Anonymization strategies

| Strategie | Resultaat |
|-----------|-----------|
| `replace` | Vervangt door `<ENTITY_TYPE>` (standaard) |
| `redact` | Verwijdert de waarde (lege string) |
| `hash` | SHA-256 hash van de originele waarde |
| `mask` | Maskeert eerste 6 tekens met `*` |

## Pattern recognizers

Alle Nederlandse pattern recognizers staan in [src/api/utils/patterns.py](../src/api/utils/patterns.py). Ze zijn Presidio `PatternRecognizer` subclasses op basis van reguliere expressies.

| Klasse | Entity type | Confidence | Beschrijving |
|--------|------------|------------|--------------|
| `DutchPhoneNumberRecognizer` | `PHONE_NUMBER` | 0.60 | NL mobiel en vast |
| `DutchIBANRecognizer` | `IBAN` | 0.55–0.60 | NL IBAN (0.60) + internationaal niet-NL (0.55) |
| `EmailRecognizer` | `EMAIL` | 0.60 | E-mailadressen |
| `DutchBSNRecognizer` | `BSN` | 0.60 | Burgerservicenummer (9 cijfers) |
| `DutchVATRecognizer` | `VAT_NUMBER` | 0.60 | BTW-nummer (`NLxxxxxxxBxx`) |
| `DutchPassportIdRecognizer` | `ID_NO` | 0.55–0.60 | Paspoort/ID-kaart |
| `CaseNumberRecognizer` | `CASE_NO` | 0.40–0.60 | Zaak-/dossiernummers (meerdere patronen) |
| `DutchDateRecognizer` | `DATE_TIME` | 0.45–0.50 | Datumnotaties (dd-mm-yyyy e.v.) |
| `DutchLicensePlateRecognizer` | `LICENSE_PLATE` | 0.50 | Nederlandse kentekens |
| `IPv4Recognizer` | `IP_ADDRESS` | 0.50 | IPv4-adressen |
| `DutchDriversLicenseRecognizer` | `DRIVERS_LICENSE` | 0.45 | Rijbewijsnummer (10 cijfers) |
| `DutchKvKRecognizer` | `KVK_NUMBER` | 0.45 | KvK-nummer (8 cijfers) |

## Helm values (selectie)

Zie `charts/openanonymiser/values.yaml` voor de volledige lijst.

```yaml
image:
  repository: mwest2020/openanonymiser
  tag: latest
  pullPolicy: IfNotPresent

app:
  env:
    uvicornServerMode: "production"
    defaultLanguage: "nl"
    defaultNlpEngine: "spacy"
    defaultSpacyModel: "nl_core_news_md"

persistence:
  enabled: false

resources:
  requests:
    cpu: 500m
    memory: 2Gi
  limits:
    cpu: 1500m
    memory: 4Gi
```
