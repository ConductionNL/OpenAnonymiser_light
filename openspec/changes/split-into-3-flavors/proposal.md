## Why

OpenAnonymiser combineert in HEAD al drie fundamenteel verschillende detectie-
benaderingen in één codebase, maar zonder expliciete scheidslijnen:

- Regex-patterns (volledig deterministisch, allemaal momenteel `enabled: false`
  in `plugins.yaml`).
- SpaCy NER (CPU, ~600MB, voorspelbare recall op PERSON/LOC/ORG).
- GLiNER (zero-shot, ~4Gi memory-request in productie, wél al actief).

De adapters voor transformer- en LLM-gebaseerde detectie bestaan (lazy imports
in `plugin_loader.py`), maar zijn ongebruikt. Het resultaat is dat nieuwe devs
niet kunnen afleiden welke entities bij welke engine horen, waarom GLiNER
4Gi vraagt, of hoe een LLM-gebaseerde contextcheck past binnen de belofte
*"verklaarbaar, herleidbaar, reproduceerbaar"* uit het functionele overzicht.

Deze change introduceert expliciete *flavors* (smaken): één image/config per
detectie-profiel, met een vast entity-contract per flavor en een gedeelde
test-suite die ze onderling vergelijkt.

## What Changes

- **Formaliseer drie flavors** — `classic` (SpaCy + regex), `gliner`
  (GLiNER + regex), `contextual` (regex + transformer/LLM verifier).
- **Splits `plugins.yaml`** in drie flavor-configs in `src/api/config/`.
  Selectie via `PLUGINS_CONFIG` env-var (mechanisme bestaat al).
- **Entity-contract per flavor** — `ALL_SUPPORTED_ENTITIES` wordt
  flavor-specifiek opgebouwd uit de geladen plugin-config. Requests voor
  entities buiten de flavor → 422 (huidige validatielogica, nieuw toegepast
  per flavor).
- **Docker: één Dockerfile per flavor** (`Dockerfile.classic`,
  `Dockerfile.gliner`, `Dockerfile.contextual`). Flavor-specifieke
  dependency-extras in `pyproject.toml`.
- **CI-matrix**: CPU-runner test `classic` + `gliner`; GPU-runner (nightly of
  on-demand) test `contextual` en GPU-`gliner`.
- **Gedeelde contract-tests** onder `tests/contract/` die tegen ELKE flavor
  draaien en dezelfde API-belofte afdwingen (DTO-shape, HTTP-codes,
  entity-validatie).
- **Per-flavor tests** onder `tests/flavors/<flavor>/` voor engine-specifiek
  gedrag (GLiNER entity-mapping, pattern overlap-resolutie, verifier
  confusion-matrix).
- **Golden-dataset cross-flavor tests** — dezelfde input-teksten door alle
  flavors, assertions op gedeelde invarianten (bv. elk e-mail in de input
  wordt door élke flavor gedetecteerd).
- **Docs**: `docs/architecture/flavors.md` en `entity-contract.md` worden
  canoniek; README verwijst ernaar. Google Doc wordt stakeholder-facing
  samenvatting met link naar repo.

## Capabilities

### New Capabilities

- `flavor-selection`: drie gescheiden deployment-profielen met vaste
  detectie-engine-set, entity-contract en resource-profiel.
- `cross-flavor-testing`: gedeelde contract-test-suite + golden-dataset
  vergelijkings-tests die de gedragsgelijkheid op gedeelde invarianten
  bewaken.

### Modified Capabilities

- `text-only-api`: endpoints wijzigen niet van shape, maar respons krijgt
  optioneel `recognizer`-veld per entity zodat auditors kunnen zien welke
  engine een detectie deed. Request-validatie wordt flavor-specifiek
  (niet globaal `ALL_SUPPORTED_ENTITIES`).

## Impact

- **Nieuwe files**:
  - `docs/architecture/flavors.md`, `docs/architecture/entity-contract.md`
    (al aangemaakt in deze branch)
  - `src/api/config/plugins.classic.yaml`, `plugins.gliner.yaml`,
    `plugins.contextual.yaml`
  - `Dockerfile.classic`, `Dockerfile.gliner`, `Dockerfile.contextual`
    (bestaande `Dockerfile` wordt vervangen of één ervan)
  - `tests/contract/`, `tests/flavors/classic/`, `tests/flavors/gliner/`,
    `tests/flavors/contextual/`, `tests/golden/` (dataset + runner)
- **Gewijzigde files**:
  - `pyproject.toml` — `[project.optional-dependencies]` voor `classic`,
    `gliner`, `contextual`. Verplaatsing van `gliner>=0.1.13` uit de
    default-dependencies.
  - `src/api/config.py` — `ALL_SUPPORTED_ENTITIES` wordt dynamisch uit
    plugin-config.
  - `src/api/dtos.py` — optioneel `recognizer`-veld in `PIIEntity`.
  - `charts/openanonymiser/values.yaml` — `flavor` value, flavor-specifieke
    `resources` presets.
  - `.github/workflows/` — CI-matrix per flavor.
  - `README.md`, `docs/01-getting-started.md`, `docs/03-configuration.md` —
    verwijzingen naar flavor-keuze.
  - `CHANGELOG.md` — entry onder komende versie.
- **Dependencies**:
  - `gliner` wordt optional-extra (niet default meer).
  - `transformers`, `torch` worden optional-extra onder `contextual`.
  - Optioneel provider-extras (`openai`, `anthropic`) onder `contextual`.
- **Resource-profiel productie**:
  - `classic`: ~1Gi memory, 0.5–1 CPU — drastisch lichter dan huidige 4Gi.
  - `gliner`: 2–4Gi (huidige staat).
  - `contextual`: 4Gi+ of externe LLM-API-kosten.
- **Version-discrepantie**: CHANGELOG zegt 1.4.0, `src/api/main.py:45` zegt
  1.3.0. Deze change synct dat naar 1.5.0 bij merge.
