# Golden dataset

Vaste set Nederlandse voorbeeldteksten met ground-truth entity-spans.
Elke flavor draait ertegen en wordt beoordeeld op dezelfde invarianten.

## Formaat

`dataset.jsonl` — één JSON-object per regel:

```json
{"id": "bsn-context", "text": "Mijn BSN is 123456782.", "entities": [{"entity_type": "BSN", "text": "123456782", "start": 12, "end": 21}]}
```

Velden:
- `id` (string, uniek) — korte slug voor referentie in rapporten.
- `text` (string) — de input-tekst, zoals-is naar `/api/v1/analyze`.
- `entities` (array) — de verwachte detecties. Volgorde doet er niet toe.
  Per entity:
  - `entity_type` (string) — één van `ALL_SUPPORTED_ENTITIES`.
  - `text` (string) — de exacte substring.
  - `start`, `end` (int) — character offsets, `text[start:end]` moet
    gelijk zijn aan `text`-veld.

## Toevoegen

1. Kies een realistische Nederlandse tekst die één of meer entity-types
   bevat. **Gebruik geen echte PII van echte personen** — gebruik
   fictieve namen, test-IBANs (NL91ABNA0417164300), etc.
2. Annoteer met exacte offsets. Verifieer met:
   ```python
   assert text[start:end] == entity_text
   ```
3. Voeg één regel toe aan `dataset.jsonl`.
4. Draai `python tests/golden/runner.py --base-url http://localhost:8081
   --dataset tests/golden/dataset.jsonl` om je voorbeeld te checken.
5. Update invarianten in `test_option_*.py` alleen als de nieuwe entity
   een nieuwe categorie is (bv. eerste IP_ADDRESS-voorbeeld).

## Invarianten

Per definitie moet **élke flavor** de volgende entity-types detecteren:

- EMAIL, PHONE_NUMBER, IBAN, DATE_TIME — pure regex, deterministisch.
- PERSON, LOCATION, ORGANIZATION — NER-gebaseerd; recall-bandbreedte
  per flavor (zie `test_option_*.py` voor drempelwaarden).

BSN/ID_NO/DRIVERS_LICENSE/etc. zijn pattern-gebaseerd; recall ≈ 100 %
zolang het pattern raakt. Contextuele disambiguation (is-het-echt-een-
BSN) komt pas in de `contextual`-flavor.
