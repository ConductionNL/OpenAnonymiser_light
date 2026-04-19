# OpenAnonymiser — Flavors (architectuur & stavaza)

> **Status:** concept (skeleton v0.2) — wordt iteratief ingevuld.
> **Geldig voor HEAD op:** `feature/3-flavors-design` branch, gebaseerd op CHANGELOG v1.4.0 (2026-04-03).
> **Canonieke bron:** dit document. Google Docs samenvattingen verwijzen hiernaar.

## 1. Waarom drie smaken

OpenAnonymiser heeft drie fundamenteel verschillende detectiemethoden — elk met
eigen resource-profiel, kwaliteits-profiel en deployment-model. In plaats van
één image/config die alles tegelijk doet, splitsen we dit in drie expliciete
*flavors* zodat:

- **Devs** weten welke entities/engines bij welke smaak horen — geen verwarring
  over "werkt X in Y?".
- **Operators** per omgeving de juiste resource-eisen kennen (CPU, GPU,
  externe afhankelijkheden).
- **Auditors** per request kunnen herleiden welke engine een detectie deed.
- **Clients** kunnen kiezen tussen determinisme en dekking.
- **Deployment-keuze** expliciet wordt: self-contained sidecar (bv. Nextcloud-
  app) vs. managed SaaS vs. SaaS-met-externe-afhankelijkheid.

## 2. Stavaza — huidige codebase (HEAD)

Wat er op dit moment in de repo staat, los van de drie-smaken-ambitie:

| Aspect | Huidige staat | Referentie |
|---|---|---|
| Versie (CHANGELOG) | 1.4.0 (2026-04-03) | `CHANGELOG.md` |
| Versie (FastAPI app) | 1.3.0 | `src/api/main.py:45` |
| Plugin-architectuur | Aanwezig, ondersteunt types `pattern`, `spacy`, `transformer`, `gliner`, `llm` | `src/api/utils/plugin_loader.py` |
| Actieve NER (development) | **GLiNER** (vervangt SpacyRecognizer wanneer enabled) | `src/api/services/text_analyzer.py:58-64`, `src/api/plugins.yaml:69-82` |
| Actieve NER (main/staging) | **SpaCy only** (geen GLiNER-plugin-entry in hun `plugins.yaml`) | `origin/main:src/api/plugins.yaml` |
| Pattern recognizers — **development** | **Allemaal `enabled: false`** | `src/api/plugins.yaml:20-67` |
| Pattern recognizers — **main / staging** | **Allemaal `enabled: true`** | `origin/main:src/api/plugins.yaml` |
| Transformer adapter | Stub aanwezig (lazy import), **geen actieve plugin** | `src/api/utils/adapters/` (transformer_adapter) |
| LLM adapter | Stub aanwezig (lazy import), **geen actieve plugin** | `src/api/utils/adapters/` (llm_adapter) |
| Engine-switch op request | `nlp_engine` bestaat in oudere docs, **niet in huidige DTO** | `src/api/dtos.py` |
| Resource-eis prod (K8s) | 4Gi memory, 1 worker — GLiNER + SpaCy + mdeberta drukken het op | `git log --oneline \| head -5` |
| Entity-validatie | Geen request-level validatie op "welke entities mogen bij welke engine" | — |

**Observaties:**
- De plugin-architectuur **is de enabler** voor flavors — we bouwen niets
  fundamenteel nieuws, we formaliseren wat er al half staat.
- **Branch → flavor-mapping (de facto):**
  - `main` en `staging` ≈ **flavor 1 (classic)** — SpaCy + alle regex
    patterns aan, geen GLiNER.
  - `development` ≈ **flavor 2 (gpu)**, maar **incompleet**: GLiNER staat
    aan, regex-patterns staan uit. Vormvaste entities (EMAIL/IBAN/BSN/
    PHONE/DATE_TIME) worden dan niet gedetecteerd. Dit is geen gewenste
    flavor-config maar een historisch artefact van het inschakelen van
    GLiNER.
- Voor flavor 2 moeten de regex-patterns **ook aan** blijven — GLiNER is
  niet precies voor vormvaste entities.
- De memory-druk uit recente commits laat zien dat *één image die alles doet*
  duur is in K8s. Per flavor een eigen image is goedkoper.

## 3. De drie flavors

| # | Naam | Detectie | Resource | Deployment-model | Belofte |
|---|---|---|---|---|---|
| 1 | **classic** | SpaCy NER + regex patterns | CPU, ~600MB image, ~1Gi mem | Self-contained "in-het-doosje": sidecar, Nextcloud-app, edge-deploy, on-prem appliance | 100 % verklaarbaar, deterministisch per input, geen externe calls |
| 2 | **gpu** | Transformer-NER (GLiNER nu, swap-baar) + regex patterns | **GPU verplicht**, ~2.5GB+ image, ≥4Gi mem | Managed SaaS of eigen K8s met GPU-node | Hogere recall, zero-shot custom entities, semi-verklaarbaar (score per span) |
| 3 | **contextual** | SpaCy/regex kandidaten → Transformer/LLM *verifier* | GPU én/of externe LLM-API | Managed SaaS met **externe afhankelijkheid** (API-provider of on-prem GPU-model-server) | Contextueel, verifier-only (geen vrije detectie), audit-trail behouden |

### 3.1 Flavor 1 — classic ("in het doosje")

**Engines:** SpaCy `nl_core_news_md` (prod) / `nl_core_news_lg` (dev) voor
PERSON/LOCATION/ORGANIZATION; `patterns.py` regex-recognizers voor vormvaste
entities (EMAIL, PHONE, IBAN, BSN, DATE_TIME, DRIVERS_LICENSE, etc.).

**Deployment-profiel:** één app, alles in de container, geen externe
afhankelijkheden. Geschikt voor:
- Sidecar naast andere services.
- Nextcloud-app / per-klant-deployment bij gemeentes.
- On-prem appliance waar GPU of externe API geen optie is.
- Air-gapped omgevingen.

**Wanneer kiezen:** default voor omgevingen waar reproduceerbaarheid, audit-
baarheid en *soevereiniteit* boven recall gaan. Voldoet aan de belofte in
het externe functioneel-overzicht: *"verklaarbaar, herleidbaar,
reproduceerbaar — in tegenstelling tot veel LLM-modellen"*.

**Status:** dit is effectief wat er op `main` en `staging` draait. Ontbreekt
nog: expliciete flavor-config-file, CI-tag, deployment-documentatie.

### 3.2 Flavor 2 — gpu (engine-agnostisch transformer-NER)

**Engines:** transformer-gebaseerde NER (vandaag: GLiNER
`urchade/gliner_multi_pii-v1`, later eventueel een andere transformer) +
regex-patterns voor vormvaste entities. De naam `gpu` beschrijft het
resource-profiel, niet de engine — dit is bewust, zodat we GLiNER later
kunnen swappen voor bv. een Dutch BERT-NER zonder hernoeming.

**Deployment-profiel:** SaaS / managed API. Draait op infrastructuur met
GPU-nodes; CPU-only is technisch mogelijk maar niet ondersteund als
deployment-target (te langzaam en geheugen-intensief voor zinnige
productie-latency).

**Wanneer kiezen:** hogere recall gewenst, custom entity-types die niet in
SpaCy zitten (via `entity_mapping`), of grotere documenten waar SpaCy te
veel faalt.

**Status:** op `development` gedeeltelijk actief, maar **incompleet** —
regex-patterns staan uit, dus vormvaste entities missen. Bij flavor-split
moeten patterns weer aan in de `gpu`-config.

### 3.3 Flavor 3 — contextual

**Engines:** SpaCy NER + regex voor *candidate extraction*, gevolgd door een
Transformer of LLM die per kandidaat *verifieert* of het inderdaad een PII-span
is. LLM wordt **niet** als vrije detector gebruikt — dat zou de
verklaarbaarheids-belofte breken.

**Deployment-profiel:** SaaS met externe afhankelijkheid — ofwel een
externe LLM-API (OpenAI, Anthropic, Azure OpenAI), ofwel een dedicated
GPU-gehoste transformer. Beide vereisen een aparte lifecycle dan de
app-container zelf.

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
    plugins.gpu.yaml
    plugins.contextual.yaml
```

Drie losse Dockerfiles (`Dockerfile.classic`, `Dockerfile.gpu`,
`Dockerfile.contextual`) met per-flavor dependency-extras via `uv sync
--extra <flavor>`. Geen ARG-ketens: expliciet en auditbaar.

## 5. Entity-contract per flavor

Zie: [`entity-contract.md`](./entity-contract.md).

Kern: elke flavor declareert welke entities hij *mag* claimen. Request met
`entities: [X]` waar X niet bij de actieve flavor hoort → 422 validatiefout
(mechanisme bestaat al op applicatie-niveau, wordt flavor-specifiek).

## 6. Resource-profiel (indicatief)

| Flavor | Image size | Memory request | CPU | GPU | Externe deps | Cold start |
|---|---|---|---|---|---|---|
| classic | ~600 MB | 512Mi – 1Gi | 0.5 – 1 core | nee | geen | ~5s |
| gpu | ~2.5 GB | 4 Gi+ | 1 – 2 cores | **ja, verplicht** | geen | ~20s |
| contextual | ~3 GB (+ externe API) | 4 Gi+ | 2+ cores | ja (of externe API) | LLM-API of GPU-model-server | ~30s |

*Getallen zijn grove schattingen uit recente commit-geschiedenis, niet gemeten.*

## 7. Testmatrix

- **CPU-only CI** (GitHub Actions, altijd): `classic` volledig; contract-tests
  voor alle flavors (zonder engines te starten, op DTO/config-niveau).
- **GPU runner** (nightly of on-demand): `gpu` en `contextual` (met mock
  LLM-provider voor contextual-unit-tests).
- Per flavor eigen test-suite tegen de eigen plugin-config.
- Golden-dataset draait cross-flavor met shared invarianten (zie §5 en
  `openspec/changes/split-into-3-flavors/design.md`).

## 8. Open vragen

Te beslissen vóór implementatie-start:

1. **Naamgeving flavors** — besloten: `classic / gpu / contextual`. Reden
   voor `gpu` (i.p.v. `gliner`): engine-agnostisch; we willen GLiNER kunnen
   swappen voor een andere transformer zonder hernoeming.
2. **Image-strategie** — besloten: drie losse `Dockerfile.<flavor>`.
3. **Default flavor per omgeving** —
   - `dev` / `staging`: welke? (Voorstel: `classic` voor snelle feedback.)
   - `acceptatie`: `gpu` (gelijk aan SaaS-productie)?
   - `productie-SaaS`: `gpu` of `contextual` afhankelijk van klant.
   - **On-prem bij klant (Nextcloud/sidecar)**: altijd `classic`.
4. **`development`-branch schoonmaken** — huidige state (GLiNER aan, patterns
   uit) is een incomplete `gpu`-flavor. Bij implementatie: patterns weer aan
   óf de branch hernoemen naar wat het is.
5. **Verifier-laag voor contextual** — on-prem transformer (mdeberta staat
   al in image volgens commits) of externe LLM-API? Mogelijk beide als
   provider-configuratie.
6. **Entity-matrix** — welke entities *moet* elke flavor minimaal dekken
   om de naam te verdienen? (Zie `entity-contract.md`.)
7. **Versie-discrepantie** — CHANGELOG zegt 1.4.0, `main.py` zegt 1.3.0.
   Los op vóór de flavor-split om verwarring te voorkomen.
8. **Transformer-swap-strategie voor gpu-flavor** — willen we meerdere
   transformer-engines ondersteunen (GLiNER én bv. Dutch-BERT-NER), of één
   default met config-override?
9. **Deployment-target per flavor — herziening (2026-04-19)** — de huidige
   §3 en `design.md §3` stellen *classic = Nextcloud/sidecar* en *gpu =
   managed SaaS op Cyso K8s*. Een alternatieve mapping die beter matcht met
   de bestaande realiteit is geopperd:
   - `classic` (CPU-only, `:main`/`:acc`/`:dev`) → **Cyso clusters**
     (dev/staging/prod). Dit is wat er feitelijk al draait; de flavor-split
     formaliseert het.
   - `gpu` → **niet naar Cyso** (geen GPU-nodes, ~75s/call op CPU =
     onbruikbaar). Aparte GPU-host / managed GPU-cluster met eigen runbook.
   - `contextual` → **in-Nextcloud** (sidecar/app release-artefact),
     buiten Cyso.

   Onder deze mapping swappen classic en contextual van plek t.o.v. de
   huidige §3. Strategisch kader: "meerdere publish-flows nu; na ~6 maanden
   resteert één productief flavor" — dus investeer niet in drie volledige
   infra-pipelines tegelijk. Classic CI blokkerend op PR-merge; gpu +
   contextual als losse/nachtelijke builds met eigen triggers.

   **Te beslissen:** bevestigen → §3, `design.md §3`, en §4 herschrijven om
   deze mapping weer te geven.

## 9. Relatie tot andere documenten

- Externe functioneel overzicht (Google Doc): *description* van wat de
  service kan. Dit document is *hoe de interne architectuur dat oplevert*.
  Google Doc verwijst naar deze file voor authoritative state.
- `openspec/changes/split-into-3-flavors/` — de concrete change-proposal
  die bij dit document hoort.
- `docs/03-configuration.md` — eindgebruiker-facing: hoe configureer je
  de service. Wordt na flavor-split bijgewerkt met flavor-keuze.
