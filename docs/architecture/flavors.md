# OpenAnonymiser — Flavors (architectuur & stavaza)

> **Status:** concept (skeleton v0.1) — wordt iteratief ingevuld.
> **Geldig voor HEAD op:** `feature/3-flavors-design` branch, gebaseerd op CHANGELOG v1.4.0 (2026-04-03).
> **Canonieke bron:** dit document. Google Docs samenvattingen verwijzen hiernaar.

## 1. Waarom drie smaken

OpenAnonymiser heeft drie fundamenteel verschillende detectiemethoden — elk met
eigen resource-profiel, kwaliteits-profiel en audit-profiel. In plaats van
één image/config die alles tegelijk doet, splitsen we dit in drie expliciete
*flavors* zodat:

- **Devs** weten welke entities/engines bij welke smaak horen — geen verwarring
  over "werkt X in Y?".
- **Operators** per omgeving de juiste resource-eisen kennen (CPU vs GPU,
  memory footprint).
- **Auditors** per request kunnen herleiden welke engine een detectie deed.
- **Clients** kunnen kiezen tussen determinisme en dekking.

## 2. Stavaza — huidige codebase (HEAD)

Wat er op dit moment in de repo staat, los van de drie-smaken-ambitie:

| Aspect | Huidige staat | Referentie |
|---|---|---|
| Versie (CHANGELOG) | 1.4.0 (2026-04-03) | `CHANGELOG.md` |
| Versie (FastAPI app) | 1.3.0 | `src/api/main.py:45` |
| Plugin-architectuur | Aanwezig, ondersteunt types `pattern`, `spacy`, `transformer`, `gliner`, `llm` | `src/api/utils/plugin_loader.py` |
| Actieve NER | **SpaCy + GLiNER** (GLiNER vervangt SpacyRecognizer wanneer enabled) | `src/api/services/text_analyzer.py:58-64`, `src/api/plugins.yaml:69-82` |
| Pattern recognizers | **Allemaal disabled** in `plugins.yaml` | `src/api/plugins.yaml:20-67` |
| Transformer adapter | Stub aanwezig (lazy import), **geen actieve plugin** | `src/api/utils/adapters/` (transformer_adapter) |
| LLM adapter | Stub aanwezig (lazy import), **geen actieve plugin** | `src/api/utils/adapters/` (llm_adapter) |
| Engine-switch op request | `nlp_engine` bestaat in oudere docs, **niet in huidige DTO** | `src/api/dtos.py` |
| Resource-eis prod (K8s) | 4Gi memory, 1 worker — GLiNER + SpaCy + mdeberta drukken het op | `git log --oneline \| head -5` |
| Entity-validatie | Geen request-level validatie op "welke entities mogen bij welke engine" | — |

**Observaties:**
- De plugin-architectuur **is de enabler** voor flavors — we bouwen niets
  fundamenteel nieuws, we formaliseren wat er al half staat.
- De huidige `plugins.yaml` configuratie komt overeen met wat wij *flavor 2*
  gaan noemen (zie §3). De pattern-laag staat uit en moet voor *flavor 1*
  weer aan.
- De memory-druk uit recente commits laat zien dat *één image die alles doet*
  duur is in K8s. Per flavor een eigen image is goedkoper.

## 3. De drie flavors

| # | Naam | Detectie | Resource | Belofte | Positionering |
|---|---|---|---|---|---|
| 1 | **classic** | SpaCy NER + regex patterns | CPU, ~600MB image, ~1Gi mem | 100 % verklaarbaar, deterministisch per input | Default, edge-deployable, auditbaar |
| 2 | **gliner** | GLiNER (+ optioneel regex) | CPU OK, ~2.5GB image, ~4Gi mem (GPU optioneel voor snelheid) | Zero-shot custom entities, semi-verklaarbaar (score per span) | Hogere recall, nieuwe entity-types zonder hertraining |
| 3 | **contextual** | SpaCy chunking → Transformer/LLM *verifier* op regex-kandidaten | GPU of externe LLM-API | Contextueel, verifier-only (geen vrije detectie) | BSN/documentnummers waar regex false-positives geeft |

### 3.1 Flavor 1 — classic

**Engines:** SpaCy `nl_core_news_md` (prod) / `nl_core_news_lg` (dev) voor
PERSON/LOCATION/ORGANIZATION; `patterns.py` regex-recognizers voor vormvaste
entities (EMAIL, PHONE, IBAN, BSN, DATE_TIME, DRIVERS_LICENSE, etc.).

**Wanneer kiezen:** default voor productie-omgevingen waar reproduceerbaarheid
en auditbaarheid boven recall gaan. Voldoet aan de belofte in het externe
functioneel-overzicht: *"verklaarbaar, herleidbaar, reproduceerbaar — in
tegenstelling tot veel LLM-modellen"*.

**Status:** bouwstenen aanwezig, maar patterns staan nu uit in `plugins.yaml`.
Flavor-specifieke config-file nodig (§4).

### 3.2 Flavor 2 — gliner

**Engines:** `urchade/gliner_multi_pii-v1` voor NER; optioneel regex-patterns
voor vormvaste entities waar GLiNER minder betrouwbaar is.

**Wanneer kiezen:** hogere recall gewenst, of custom entity-types die niet in
SpaCy zitten (via `entity_mapping` in `plugins.yaml`).

**Status:** **huidige default in repo** (GLiNER enabled in `plugins.yaml`).
Memory-footprint al gemerkt in productie (4Gi request, 1 worker).

### 3.3 Flavor 3 — contextual

**Engines:** SpaCy NER + regex voor *candidate extraction*, gevolgd door een
Transformer of LLM die per kandidaat *verifieert* of het inderdaad een PII-span
is. LLM wordt **niet** als vrije detector gebruikt — dat zou de
verklaarbaarheids-belofte breken.

**Use-case:** BSN detection — regex vindt alle 9-cijferige strings, LLM/BERT
beslist op basis van context of het een BSN is ("BSN: 123456789" ja;
"artikelnummer 123456789" nee).

**Status:** adapters bestaan (lazy imports), **geen actieve plugin**. Verifier-
wrapper nog te bouwen. Open vraag: on-premise transformer vs externe LLM-API
(kosten, latency, data-lek-risico).

## 4. Hoe kies je een flavor?

**Principe:** één flavor per deployment/image. Niet dynamisch per request
switchen — dat maakt audit-trail onduidelijk en verhoogt resource-gebruik
(alle engines geladen).

**Configuratie-mechanisme:** `plugins.yaml` per flavor, geselecteerd via
`PLUGINS_CONFIG` env-var (mechanisme bestaat al in `plugin_loader.py:123`).

Voorstel (onder discussie):

```
src/api/
  config/
    plugins.classic.yaml
    plugins.gliner.yaml
    plugins.contextual.yaml
```

Dockerfile ARG `FLAVOR=classic` bepaalt welke config in image terechtkomt en
welke dependencies geïnstalleerd worden (`uv sync --extra <flavor>`).

## 5. Entity-contract per flavor

Zie: [`entity-contract.md`](./entity-contract.md).

Kern: elke flavor declareert welke entities hij *mag* claimen. Request met
`entities: [X]` waar X niet bij de actieve flavor hoort → 422 validatiefout
(mechanisme bestaat al op applicatie-niveau, wordt flavor-specifiek).

## 6. Resource-profiel (indicatief)

| Flavor | Image size | Memory request | CPU | GPU | Cold start |
|---|---|---|---|---|---|
| classic | ~600 MB | 512Mi – 1Gi | 0.5 – 1 core | nee | ~5s |
| gliner | ~2.5 GB | 2 – 4 Gi | 1 – 2 cores | optioneel | ~20s |
| contextual | ~3 GB + LLM-API | 4 Gi + | 2+ cores | ja (of externe API) | ~30s |

*Getallen zijn grove schattingen uit recente commit-geschiedenis, niet gemeten.*

## 7. Testmatrix

- **CPU-only CI** (GitHub Actions, altijd): `classic` en `gliner` (CPU-mode).
- **GPU runner** (nightly of on-demand): `contextual`, GPU-`gliner`.
- Per flavor eigen test-suite tegen de eigen plugin-config, geen cross-flavor
  tests behalve de gedeelde DTO-contract-tests.

## 8. Open vragen

Te beslissen vóór implementatie-start:

1. **Naamgeving flavors** — `classic / gliner / contextual` of andere labels?
2. **Image-strategie** — één Dockerfile met `ARG FLAVOR`, of drie aparte
   `Dockerfile.<flavor>`? Voorkeur: drie, want saaier/audit-baar.
3. **Default flavor voor dev-omgeving** — `classic` (snel) of `gliner` (gelijk
   aan prod)?
4. **Verifier-laag voor contextual** — on-prem transformer (mdeberta staat
   al in image volgens commits) of externe LLM-API?
5. **Entity-matrix** — welke entities *moet* elke flavor minimaal dekken
   om de naam te verdienen? (Zie `entity-contract.md`.)
6. **Versie-discrepantie** — CHANGELOG zegt 1.4.0, `main.py` zegt 1.3.0.
   Los op vóór de flavor-split om verwarring te voorkomen.

## 9. Relatie tot andere documenten

- Externe functioneel overzicht (Google Doc): *description* van wat de
  service kan. Dit document is *hoe de interne architectuur dat oplevert*.
  Google Doc verwijst naar deze file voor authoritative state.
- `openspec/changes/split-into-3-flavors/` — de concrete change-proposal
  die bij dit document hoort.
- `docs/03-configuration.md` — eindgebruiker-facing: hoe configureer je
  de service. Wordt na flavor-split bijgewerkt met flavor-keuze.
