# API Reference

Base URL: `https://api.openanonymiser.commonground.nu`
Swagger UI: `{BASE}/api/v1/docs`
OpenAPI JSON: `{BASE}/api/v1/openapi.json`

---

## GET /api/v1/health

Liveness check.

```bash
curl -s {BASE}/api/v1/health
```

Response:
```json
{"ping": "pong"}
```

---

## POST /api/v1/analyze

Detecteer PII-entiteiten in tekst. Geeft posities, types en confidence scores terug zonder de tekst te wijzigen.

### Request

| Veld | Type | Verplicht | Standaard | Beschrijving |
|------|------|-----------|-----------|--------------|
| `text` | string | ✓ | — | Te analyseren tekst |
| `language` | string | | `nl` | Taalcode (`nl`, `en`) |
| `entities` | string[] | | [standaard set](#standaard-entities) | Filter op entiteittypes |

### Voorbeeld

```bash
curl -s -X POST {BASE}/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Jan Jansen woont in Amsterdam. IBAN: NL91ABNA0417164300.",
    "language": "nl",
    "entities": ["PERSON", "LOCATION", "IBAN"]
  }'
```

### Response

```json
{
  "pii_entities": [
    {"entity_type": "PERSON",   "text": "Jan Jansen",          "start": 0,  "end": 10, "score": 0.85},
    {"entity_type": "LOCATION", "text": "Amsterdam",           "start": 20, "end": 29, "score": 0.85},
    {"entity_type": "IBAN",     "text": "NL91ABNA0417164300",  "start": 37, "end": 55, "score": 0.6}
  ],
  "text_length": 56,
  "processing_time_ms": 12,
  "language": "nl"
}
```

---

## POST /api/v1/anonymize

Anonimiseer PII in tekst. Gebruikt Presidio's `AnonymizerEngine` voor vervanging.

### Request

| Veld | Type | Verplicht | Standaard | Beschrijving |
|------|------|-----------|-----------|--------------|
| `text` | string | ✓ | — | Te anonimiseren tekst |
| `language` | string | | `nl` | Taalcode (`nl`, `en`) |
| `entities` | string[] | | [standaard set](#standaard-entities) | Filter op entiteittypes |
| `anonymization_strategy` | string | | `replace` | Zie [strategies](#anonymization-strategies) |

### Anonymization strategies

| Strategie | Resultaat |
|-----------|-----------|
| `replace` | Vervangt door `<ENTITY_TYPE>` (standaard) |
| `redact` | Verwijdert de waarde (lege string) |
| `hash` | SHA-256 hash van de originele waarde |
| `mask` | Maskeert eerste 6 tekens met `*` |

### Voorbeeld

```bash
curl -s -X POST {BASE}/api/v1/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Mail Jan op jan@example.com of bel 0612345678.",
    "language": "nl",
    "anonymization_strategy": "replace"
  }'
```

### Response

```json
{
  "original_text": "Mail Jan op jan@example.com of bel 0612345678.",
  "anonymized_text": "Mail <PERSON> op <EMAIL> of bel <PHONE_NUMBER>.",
  "entities_found": [
    {"entity_type": "PERSON",       "text": "Jan",           "start": 5,  "end": 8,  "score": 0.85},
    {"entity_type": "EMAIL",        "text": "jan@example.com","start": 12, "end": 27, "score": 0.6},
    {"entity_type": "PHONE_NUMBER", "text": "0612345678",    "start": 35, "end": 45, "score": 0.6}
  ],
  "text_length": 46,
  "processing_time_ms": 11,
  "anonymization_strategy": "replace"
}
```

---

## Ondersteunde entiteittypes

### Standaard entities

Wanneer `entities` niet meegegeven wordt, worden deze types gedetecteerd:

`PERSON` · `LOCATION` · `ORGANIZATION` · `PHONE_NUMBER` · `EMAIL` · `IBAN` · `BSN` · `DATE_TIME`

### Alle ondersteunde types

| Entiteit | Methode | Score | Beschrijving |
|---------|---------|-------|--------------|
| `PERSON` | SpaCy NER | 0.85 | Persoonsamen |
| `LOCATION` | SpaCy NER | 0.85 | Plaatsnamen, landen (incl. GPE) |
| `ORGANIZATION` | SpaCy NER | 0.85 | Organisatienamen |
| `PHONE_NUMBER` | Pattern | 0.60 | NL mobiel en vast |
| `EMAIL` | Pattern | 0.60 | E-mailadressen |
| `IBAN` | Pattern | 0.60 | NL IBAN + internationaal (niet-NL) |
| `BSN` | Pattern | 0.60 | Burgerservicenummer (9 cijfers) |
| `VAT_NUMBER` | Pattern | 0.60 | BTW-nummer (`NLxxxxxxxBxx`) |
| `ID_NO` | Pattern | 0.55–0.60 | Paspoort / identiteitskaart |
| `CASE_NO` | Pattern | 0.45–0.60 | Zaak-/dossiernummers |
| `DATE_TIME` | Pattern | 0.45–0.50 | Datumnotaties |
| `LICENSE_PLATE` | Pattern | 0.50 | Nederlandse kentekens |
| `IP_ADDRESS` | Pattern | 0.50 | IPv4-adressen |
| `DRIVERS_LICENSE` | Pattern | 0.45 | Rijbewijsnummer (10 cijfers) |
| `KVK_NUMBER` | Pattern | 0.45 | KvK-nummer (8 cijfers) |

> **Let op:** lage scores (≤ 0.50) hebben een verhoogd risico op false positives. Gebruik `entities`-filter om ruis te beperken. SpaCy NER kan ook false positives geven op korte/ambigue tokens.

---

## Voorbeeld: alle entiteittypes in één call

```bash
curl -s -X POST {BASE}/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Jan Jansen (BSN: 111222333) woont in Amsterdam. Gemeente Utrecht is zijn werkgever. Mail: jan@example.com, Tel: 0612345678. IBAN: NL91ABNA0417164300. Rijbewijs: 1234567890. Paspoort: AB1234561. KvK: 12345678. BTW: NL123456789B01. Kenteken: AB-12-CD. IP: 192.168.1.1. Zaak: Z-2023-12345. Datum: 15-03-2023.",
    "language": "nl",
    "entities": ["PERSON","LOCATION","ORGANIZATION","PHONE_NUMBER","EMAIL","IBAN","BSN","DATE_TIME","ID_NO","DRIVERS_LICENSE","VAT_NUMBER","KVK_NUMBER","LICENSE_PLATE","IP_ADDRESS","CASE_NO"]
  }'
```

Verwacht resultaat (afgekorte weergave):

```json
{
  "pii_entities": [
    {"entity_type": "PERSON",       "text": "Jan Jansen",         "score": 0.85},
    {"entity_type": "LOCATION",     "text": "Amsterdam",          "score": 0.85},
    {"entity_type": "LOCATION",     "text": "Utrecht",            "score": 0.85},
    {"entity_type": "BSN",          "text": "111222333",          "score": 0.60},
    {"entity_type": "EMAIL",        "text": "jan@example.com",    "score": 0.60},
    {"entity_type": "PHONE_NUMBER", "text": "0612345678",         "score": 0.60},
    {"entity_type": "IBAN",         "text": "NL91ABNA0417164300", "score": 0.60},
    {"entity_type": "ID_NO",        "text": "AB1234561",          "score": 0.60},
    {"entity_type": "VAT_NUMBER",   "text": "NL123456789B01",     "score": 0.60},
    {"entity_type": "CASE_NO",      "text": "Z-2023-12345",       "score": 0.55},
    {"entity_type": "LICENSE_PLATE","text": "AB-12-CD",           "score": 0.50},
    {"entity_type": "IP_ADDRESS",   "text": "192.168.1.1",        "score": 0.50},
    {"entity_type": "DATE_TIME",    "text": "15-03-2023",         "score": 0.50},
    {"entity_type": "DRIVERS_LICENSE","text": "1234567890",       "score": 0.45},
    {"entity_type": "KVK_NUMBER",   "text": "12345678",           "score": 0.45}
  ],
  "text_length": 305,
  "processing_time_ms": 12,
  "language": "nl"
}
```

---

## Troubleshooting

- **Validation Error**: controleer verplichte velden en JSON-syntax.
- **"No matching recognizers"**: gevraagd entiteittype bestaat niet — zie tabel hierboven.
- **Geen entiteiten gevonden**: probeer zonder `entities` filter, of controleer `language`.
- **Dubbele matches op zelfde span**: Presidio retourneert meerdere types per span als scores verschillen. Filter op het gewenste type of gebruik een hogere score als drempel.
- **NER false positives**: SpaCy NER (score 0.85) kan korte/ambigue tokens verkeerd taggen. Vergelijk met pattern-erkende waarden (lagere scores) voor verificatie.
