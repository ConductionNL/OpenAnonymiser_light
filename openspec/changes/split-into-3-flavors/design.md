## Context

De plugin-architectuur in `src/api/utils/plugin_loader.py` ondersteunt al
vijf plugin-typen (`pattern`, `spacy`, `transformer`, `gliner`, `llm`) en
leest de actieve set uit `plugins.yaml`. De selectie gebeurt via env-var
`PLUGINS_CONFIG`. Dit is feitelijk al een flavor-switch — hij wordt alleen
niet zo gebruikt.

De branch-state in HEAD bevestigt dat de flavor-splitsing de facto al
bestaat, maar impliciet en niet gedocumenteerd:
- `origin/main` en `origin/staging`: SpaCy + alle regex-patterns enabled,
  geen GLiNER. = **classic**.
- `origin/development`: GLiNER enabled, alle regex-patterns disabled, geen
  transformer/LLM. = **incomplete gpu** (mist vormvaste entities).

De adapters voor transformer en LLM bestaan als lazy imports maar hebben
geen actieve plugin-entry.

In de productie-omgeving (op development-tags) is de memory-druk recent
opgeschaald naar 4Gi met 1 worker (zie commits `3f1bd76`, `01955c7`). Dat is
een directe consequentie van GLiNER + mdeberta + SpaCy in één image draaien.

Dit ontwerp formaliseert drie flavors, bouwt de test-infrastructuur die ze
onderling bewaakt, en lost en-passant de versie-discrepantie tussen
CHANGELOG (1.4.0) en `main.py` (1.3.0) op.

## Goals / Non-Goals

**Goals:**
- Eén flavor = één image = één `plugins.yaml` = voorspelbaar resource-profiel.
- Entity-contract per flavor dat door code + tests + docs wordt gesynct.
- Gedeelde contract-test-suite die gedrag op DTO-niveau tussen flavors
  bewaakt.
- Golden-dataset test dat shared-invariant-gedrag (bv. regex-entities) over
  alle flavors consistent is.
- `classic` wordt default voor omgevingen die reproduceerbaarheid boven
  recall zetten.

**Non-Goals:**
- Runtime-switch tussen flavors op request-niveau (bewust niet — audit-
  trail en memory-footprint).
- Herschrijven van bestaande recognizers.
- Nieuwe entity-types introduceren (alleen herverdelen over flavors).
- LLM als vrije entity-detector (alleen als *verifier* op pattern-kandidaten,
  zie decision 4).

## Decisions

### 1. Naamgeving: `classic / gpu / contextual`

- **Keuze:** deze drie labels.
- **Reden:**
  - `classic` past bij de "saaie-maar-auditbare" belofte en bij het "in-het-
    doosje"-deployment-profiel (sidecar, Nextcloud-app, on-prem appliance).
  - `gpu` beschrijft het resource-profiel en is **engine-agnostisch** —
    we willen GLiNER later kunnen vervangen door een Dutch-BERT-NER of een
    andere transformer zonder opnieuw te hernoemen. De naam beschrijft wat
    de operator moet leveren (een GPU), niet welk specifiek model er
    toevallig draait.
  - `contextual` beschrijft de toegevoegde waarde (context-verificatie)
    zonder "LLM" in de naam te zetten (die term staat negatief in het
    externe functioneel-overzicht).
- **Alternatief overwogen:** `gliner` voor flavor 2. Afgewezen: koppelt
  de naam aan één specifieke engine, maakt engine-swap rommelig.
- **Alternatief overwogen:** `light / accurate / contextual`. Afgewezen
  omdat "accurate" suggereert dat `classic` onnauwkeurig is — niet waar
  voor pattern-entities.

### 2. Selectie-mechanisme: env-var `PLUGINS_CONFIG`

- **Keuze:** hergebruik het bestaande mechanisme in
  `plugin_loader.py:123`. Drie config-files naast elkaar in
  `src/api/config/plugins.<flavor>.yaml`.
- **Reden:** minst ingrijpend, code-pad bestaat al. Geen nieuwe runtime-
  logica.
- **Alternatief:** request-parameter `flavor` in DTO. Afgewezen: forceert
  alle engines in één image, breekt audit-model.

### 3. Deployment: drie losse Dockerfiles + drie deployment-modellen

- **Keuze:** `Dockerfile.classic`, `Dockerfile.gpu`,
  `Dockerfile.contextual`. Elke file bakt eigen model-assets + selecteert
  eigen `plugins.<flavor>.yaml`.
- **Reden:** saaier, expliciet, auditbaar. Lezer hoeft geen `ARG`-ketens
  te volgen om te weten wat in de image zit.
- **Per-flavor deployment-target:**
  - `classic` — sidecar / Nextcloud-app / on-prem appliance / air-gapped.
    Eén container, geen externe deps, CPU-only.
  - `gpu` — managed SaaS op K8s met GPU-node-pool, of dedicated GPU-VM.
    Geen externe deps behalve het model (pre-baked in image).
  - `contextual` — managed SaaS met extra dependency-laag: externe LLM-API
    (OpenAI / Anthropic / Azure) of eigen GPU-model-server. Vereist
    secrets-management voor provider-credentials.
- **Consequentie:** drie CI-jobs voor images, drie Helm-values-presets,
  verschillende operationele runbooks per flavor.

### 4. Contextual-flavor: LLM/transformer als *verifier*, niet als
   *detector*

- **Keuze:** de LLM/transformer mag alleen binaire classificaties
  doen op kandidaten uit regex of SpaCy. Geen vrije extractie.
- **Reden:** behoudt de belofte *"verklaarbaar, herleidbaar"*. De audit-
  trail is: (a) regex vond kandidaat X op positie Y; (b) verifier zei
  `is_bsn=true` met score 0.92. Beide stappen reproduceerbaar.
- **Consequentie:** `contextual` voegt geen nieuwe entity-types toe t.o.v.
  `classic`, maar levert hogere precisie op BSN / ID_NO / andere
  context-gevoelige regex-entities.
- **Open:** on-premise transformer (mdeberta — staat al in image volgens
  commit `bfc541a`) of externe LLM-API? Data-lek-risico en kosten wegen
  tegen elkaar op.

### 5. Test-architectuur: drie lagen

- **Contract-tests** (`tests/contract/`): draaien tegen elke flavor via
  parametrize. Asserteren: HTTP-codes, DTO-shapes, entity-validatie-logica,
  anonymization-strategies. Deze tests hoeven geen echte engines op te
  starten (plugin-loading + config-validatie), draaien dus op CPU.
- **Per-flavor-tests** (`tests/flavors/<flavor>/`): engine-specifiek gedrag.
  Bv. pattern-overlap-resolutie in `classic`, transformer-NER entity-
  mapping in `gpu`, verifier-confusion-matrix in `contextual`.
- **Golden-dataset-tests** (`tests/golden/`): vaste set Nederlandse
  voorbeeld-teksten met ground-truth annotaties. Elke flavor draait ertegen,
  output wordt vergeleken op gedeelde invarianten (elk regex-detect moet
  in élke flavor voorkomen; recall-verschillen op NER mogen binnen
  bandbreedte).
- **Reden:** voorkomt stille drift tussen flavors en maakt recall/precision-
  verschillen zichtbaar bij elke PR.
- **Resource-consequentie:** CPU-runner draait contract-tests (alle flavors)
  + `classic` engine-tests; GPU-runner (nightly of label-triggered) draait
  `gpu` en `contextual` engine-tests. `contextual` gebruikt een mock-LLM-
  provider in unit-tests en echte provider alleen in nightly.

### 6. Entity-contract in code, niet alleen in docs

- **Keuze:** `ALL_SUPPORTED_ENTITIES` in `config.py` wordt dynamisch
  opgebouwd uit de geladen plugin-config bij startup. Niet meer een
  hardcoded lijst.
- **Reden:** single source of truth = de plugin-config. Docs worden
  afgeleid; drift tussen code en docs wordt structureel voorkomen.
- **Implementatie:** `plugin_loader.py` exposeert `supported_entities`;
  `config.py` leest deze bij startup.

### 7. Versie-sync en bump naar 1.5.0

- **Keuze:** deze change is de trigger om `main.py:45` naar 1.5.0 te tillen
  en CHANGELOG-entry te schrijven.
- **Reden:** de discrepantie is verwarrend; flavor-split is een geschikte
  momentopname.

## Risks / Trade-offs

- **Risk: CI-tijd verdrievoudigt.** Contract-tests draaien tegen drie
  flavors. → Mitigatie: parallelle jobs, GPU-runs alleen op nightly of
  label-triggered.
- **Risk: plugin-config drift.** Drie YAML-files onderhouden kan
  inconsistent raken. → Mitigatie: een `tests/contract/test_flavor_configs.py`
  die valideert dat elke config laadbaar is en dat de intersectie van
  entities (regex-basis) over alle flavors identiek is.
- **Risk: contextual-verifier is traag.** LLM-call per kandidaat kan
  p95-latency opblazen. → Mitigatie: verifier is opt-in per entity-type
  (alleen BSN/ID_NO default), batch-calls waar mogelijk.
- **Risk: main/staging draaien feitelijk al `classic`, development draait
  een incomplete `gpu`.** Teams kunnen verschillend gedrag zien per branch.
  → Mitigatie: maak de mapping expliciet in `plugins.<flavor>.yaml`-files
  en documenteer branch→flavor-default in `docs/04-deployment.md`.
- **Risk: transformer-engine-swap in de `gpu`-flavor.** Als we GLiNER
  vervangen door Dutch-BERT-NER, verandert output-shape mogelijk. →
  Mitigatie: `plugins.gpu.yaml` is de swap-point, golden-dataset-tests
  vangen regressies op bij de swap.
- **Trade-off: drie Dockerfiles betekent driedubbele onderhoudslast op
  base-image updates.** → Geaccepteerd; auditbaarheid weegt zwaarder.

## Migration Plan

1. Docs + openspec first (deze branch, al gedaan voor docs).
2. Review-ronde met team op `docs/architecture/flavors.md` +
   `entity-contract.md` + openspec-proposal. Open vragen uit flavors.md §8
   sluiten.
3. Implementatie in volgorde:
   - `plugins.classic.yaml` (pattern-recognizers weer aanzetten, GLiNER uit).
   - `Dockerfile.classic` + CI-build + smoke-test.
   - Golden-dataset + contract-test-framework.
   - `plugins.gpu.yaml` (development-state + regex-patterns weer aan).
   - `plugins.contextual.yaml` + verifier-adapter.
4. Default van dev-compose kiezen (open vraag 3 uit flavors.md).
5. Helm-chart-updates + deployment per omgeving.
6. README + user-docs bijwerken, Google Doc korten en naar repo laten
   linken.

## Open Questions

Zie `docs/architecture/flavors.md` §8 voor de lijst. Kernvragen voor review:

- Naamgeving flavors definitief?
- Default flavor per omgeving (dev / acc / prod)?
- Contextual verifier: on-prem of externe API?
- Entity-matrix: moet `classic` alle pattern-entities dekken, of AVG-kern?
