# Benchmarking

Kwaliteitsmeting van de PII-detectie per entiteitstype op basis van karakter-span precisie en recall.

## Lokaal draaien

```bash
uv run benchmarks/evaluate.py
```

Met CI-modus (exit 1 bij drempel-overtreding):

```bash
uv run benchmarks/evaluate.py --fail-on-threshold
```

## Opties

| Optie | Standaard | Beschrijving |
|-------|-----------|--------------|
| `--data` | `benchmarks/data/dutch_pii_sentences.json` | Gelabelde testdata |
| `--thresholds` | `benchmarks/thresholds.yaml` | Minimale precision/recall per entiteit |
| `--fail-on-threshold` | uit | Exit 1 als drempel niet gehaald |
| `--score-threshold` | `0.4` | Minimum Presidio confidence |
| `--iou-threshold` | `0.5` | Minimum overlap tussen voorspelling en grondwaarheid |

## Testdata uitbreiden

Voeg zinnen toe aan `benchmarks/data/dutch_pii_sentences.json`:

```json
{
  "full_text": "De factuur staat op naam van Pieter Bakker.",
  "spans": [
    {"entity_type": "PERSON", "entity_value": "Pieter Bakker", "start_position": 28, "end_position": 41}
  ]
}
```

Let op:
- `start_position` en `end_position` zijn karakter-indexen (0-gebaseerd)
- Zorg dat de zin geen andere detecteerbare entiteiten bevat die niet gelabeld zijn
- Gebruik meerdere zinnen per entiteitstype voor betrouwbaarder statistieken

## Drempels aanpassen

Bewerk `benchmarks/thresholds.yaml`. Stel drempels conservatief in — verhoog ze geleidelijk naarmate de dataset groeit.

## Veelvoorkomende valkuilen

- **10-cijferige telefoonnummers** matchen ook `DRIVERS_LICENSE` (by design in Presidio; label beide of gebruik 11-cijferig formaat)
- **Jaar-formaat nummers** (bijv. `0800-123456`) matchen ook `CASE_NO`; gebruik formaten die niet overlappen
- NER-types (PERSON, LOCATION, ORGANIZATION) hebben inherent lagere precisie dan patroon-types
