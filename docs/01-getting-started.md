# Getting Started

## Vereisten

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) als package manager
- Docker of Podman (optioneel, voor containerisatie)

## Lokaal draaien

```bash
uv venv
uv sync
uv run api.py
```

De API is bereikbaar op [http://localhost:8080/api/v1/docs](http://localhost:8080/api/v1/docs) (Swagger UI).

## Eerste verzoek

```bash
curl -s -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Jan Jansen woont op Kerkstraat 10, 1234 AB Amsterdam. IBAN: NL91ABNA0417164300.",
    "language": "nl"
  }'
```

Verwacht resultaat: een lijst met gevonden PII-entiteiten (PERSON, LOCATION, IBAN).

## Omgevingsvariabelen

Kopieer `.env.example` naar `.env` en pas aan:

```bash
cp .env.example .env
```

Standaard werkt de API met `nl_core_news_lg` in de lokale venv. Zie [03-configuration.md](03-configuration.md) voor alle opties.

## Wat detecteert de API?

| Type | Methode | Entiteiten |
|------|---------|-----------|
| Patroon (regelgebaseerd) | Presidio recognizers | IBAN, PHONE_NUMBER, EMAIL, BSN, KVK, DRIVER_LICENSE, PASSPORT, LICENSE_PLATE, VAT, IPv4, DATE |
| NER (taalmodel) | SpaCy `nl_core_news_md` | PERSON, LOCATION, ORGANIZATION, ADDRESS |

Kies expliciete `entities` in je request om te filteren, of laat leeg voor alle entiteiten.

## Volgende stappen

- [02-api-reference.md](02-api-reference.md) — alle endpoints met voorbeelden
- [03-configuration.md](03-configuration.md) — modellen, engines, env vars
- [04-deployment.md](04-deployment.md) — container en Kubernetes
