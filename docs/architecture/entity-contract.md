# Entity-contract per flavor

> **Status:** concept (skeleton v0.1). Definitieve matrix volgt na discussie
> in de openspec proposal `split-into-3-flavors`.
> Zie ook: [`flavors.md`](./flavors.md).

## Doel

Per flavor vastleggen welke entity-types hij **mag claimen**. Dit contract:

- Wordt afgedwongen op requestniveau: `entities: [X]` waar X niet bij de
  actieve flavor hoort → 422 validatiefout.
- Dient als single source of truth bij code-reviews (PR die een engine
  wijzigt moet de matrix in dezelfde commit bijwerken).
- Voorkomt dat flavor-smaken stilletjes in elkaar diffunderen.

## Huidige set (HEAD)

Alle entity-types die ergens in de code voorkomen:

| Entity | Bron | In `DEFAULT_ENTITIES` | In `ALL_SUPPORTED_ENTITIES` |
|---|---|---|---|
| PERSON | SpaCy NER, GLiNER | ✓ | ✓ |
| LOCATION | SpaCy NER, GLiNER | ✓ | ✓ |
| ORGANIZATION | SpaCy NER, GLiNER | ✓ | ✓ |
| PHONE_NUMBER | pattern (`DutchPhoneNumberRecognizer`) | ✓ | ✓ |
| EMAIL | pattern (`EmailRecognizer`) | ✓ | ✓ |
| IBAN | pattern (`DutchIBANRecognizer`) | ✓ | ✓ |
| BSN | pattern (`DutchBSNRecognizer`) | ✓ | ✓ |
| DATE_TIME | pattern (`DutchDateRecognizer`) | ✓ | ✓ |
| ID_NO | pattern (`DutchPassportIdRecognizer`) | — | ✓ |
| DRIVERS_LICENSE | pattern (`DutchDriversLicenseRecognizer`) | — | ✓ |
| CASE_NO | pattern (`CaseNumberRecognizer`) | — | ✓ |
| VAT_NUMBER | pattern (`DutchVATRecognizer`) | — | ✓ |
| KVK_NUMBER | pattern (`DutchKvKRecognizer`) | — | ✓ |
| LICENSE_PLATE | pattern (`DutchLicensePlateRecognizer`) | — | ✓ |
| IP_ADDRESS | pattern (`IPv4Recognizer`) | — | ✓ |

Bron: `src/api/config.py:19-50`.

## Voorgestelde matrix per flavor

Leidend principe:
- **Pattern = altijd precies.** Regex-entities horen bij elke flavor die pattern
  recognizers actief heeft.
- **NER-engine bepaalt** of PERSON/LOCATION/ORGANIZATION gedekt zijn.
- **Contextual** voegt *verificatie* toe op pattern-resultaten; declareert
  geen nieuwe entities, maar wél hogere precisie voor BSN/ID_NO.

| Entity | classic | gpu | contextual |
|---|---|---|---|
| PERSON | SpaCy | transformer-NER (GLiNER default) | SpaCy + verifier |
| LOCATION | SpaCy | transformer-NER (GLiNER default) | SpaCy + verifier |
| ORGANIZATION | SpaCy | transformer-NER (GLiNER default) | SpaCy + verifier |
| PHONE_NUMBER | pattern | pattern | pattern |
| EMAIL | pattern | pattern | pattern |
| IBAN | pattern | pattern | pattern |
| BSN | pattern | pattern | pattern + LLM-verifier* |
| DATE_TIME | pattern | pattern | pattern |
| ID_NO | pattern | pattern | pattern + LLM-verifier* |
| DRIVERS_LICENSE | pattern | pattern | pattern |
| CASE_NO | pattern | pattern | pattern |
| VAT_NUMBER | pattern | pattern | pattern |
| KVK_NUMBER | pattern | pattern | pattern |
| LICENSE_PLATE | pattern | pattern | pattern |
| IP_ADDRESS | pattern | pattern | pattern |
| *custom-labels* | — | ✓ (via `entity_mapping` van de transformer-NER) | ✓ |

\* *LLM-verifier* = LLM classificeert pattern-kandidaten binair
(is-dit-een-BSN ja/nee op basis van context). Geen vrije extractie.

## Validatie-regel

- Request met `entities: [X]` waar X niet in de actieve flavor's matrix staat
  → **HTTP 422**, geen stille fallback.
- Request zonder `entities` → alle entities van de flavor worden gerapporteerd.
- Response bevat per entity het `recognizer`-veld zodat clients/auditors zien
  welke engine de detectie deed (uit te breiden in DTO).

## Hoe een entity toevoegen

1. Nieuwe `PatternRecognizer`-subclass in `src/api/utils/patterns.py` (voor
   vormvaste entities) OF nieuwe entry in `plugins.yaml` onder de juiste
   flavor-config (voor NER/LLM-entities).
2. Matrix hierboven bijwerken — in dezelfde PR.
3. Test toevoegen in `tests/` — per flavor.
4. `ALL_SUPPORTED_ENTITIES` in `config.py` bijwerken.
5. CHANGELOG-entry onder de volgende versie.

## Open vragen

1. Moet *elke* flavor alle pattern-entities ondersteunen, of kan `classic`
   een minimale subset hebben (bv. alleen AVG-kern: PERSON/EMAIL/PHONE/IBAN/
   BSN/DATE_TIME)?
2. Hoe rapporteren we *onzekerheid* in responses — alleen score, of ook
   `confidence_band: {high, medium, low}` afgeleid van de engine?
3. `recognizer`-veld in response: vrijgeven of geheim houden (exposeert
   interne architectuur)?
