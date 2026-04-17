## Context

De plugin-architectuur in `src/api/utils/plugin_loader.py` ondersteunt al
vijf plugin-typen (`pattern`, `spacy`, `transformer`, `gliner`, `llm`) en
leest de actieve set uit `plugins.yaml`. De selectie gebeurt via env-var
`PLUGINS_CONFIG`. Dit is feitelijk al een flavor-switch — hij wordt alleen
niet zo gebruikt.

De huidige `plugins.yaml` representeert *flavor 2*: GLiNER actief, alle
pattern-recognizers disabled, geen transformer/LLM. De adapters voor
transformer en LLM bestaan als lazy imports maar hebben geen actieve
plugin-entry.

In de productie-omgeving is de memory-druk recent opgeschaald naar 4Gi met
1 worker (zie commits `3f1bd76`, `01955c7`). Dat is een directe consequentie
van "alles in één image".

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

### 1. Naamgeving: `classic / gliner / contextual`

- **Keuze:** deze drie labels.
- **Reden:** `classic` past bij de "saaie-maar-auditbare" belofte; `gliner`
  is engine-specifiek en eerlijk over de resource-kosten; `contextual`
  beschrijft de toegevoegde waarde (context-verificatie) zonder "LLM" in
  de naam te zetten (die term staat negatief in het externe overzicht).
- **Alternatief:** `light / accurate / contextual`. Afgewezen omdat
  "accurate" suggereert dat `classic` onnauwkeurig is — niet waar voor
  pattern-entities.
- **Open:** defenitieve keuze wordt bij review geconfirmeerd.

### 2. Selectie-mechanisme: env-var `PLUGINS_CONFIG`

- **Keuze:** hergebruik het bestaande mechanisme in
  `plugin_loader.py:123`. Drie config-files naast elkaar in
  `src/api/config/plugins.<flavor>.yaml`.
- **Reden:** minst ingrijpend, code-pad bestaat al. Geen nieuwe runtime-
  logica.
- **Alternatief:** request-parameter `flavor` in DTO. Afgewezen: forceert
  alle engines in één image, breekt audit-model.

### 3. Deployment: drie losse Dockerfiles

- **Keuze:** `Dockerfile.classic`, `Dockerfile.gliner`,
  `Dockerfile.contextual`. Elke file bakt eigen model-assets + selecteert
  eigen `plugins.<flavor>.yaml`.
- **Reden:** saaier, expliciet, auditbaar. Lezer hoeft geen `ARG`-ketens
  te volgen om te weten wat in de image zit.
- **Alternatief:** één Dockerfile met `ARG FLAVOR`. Afgewezen om
  bovenstaande redenen; past ook niet bij de CLAUDE.md-voorkeur voor
  "boring, auditable".
- **Consequentie:** drie CI-jobs voor images, drie Helm-values-presets.

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
  anonymization-strategies.
- **Per-flavor-tests** (`tests/flavors/<flavor>/`): engine-specifiek gedrag.
  Bv. GLiNER entity-mapping correct, pattern-overlap-resolutie in `classic`,
  verifier-confusion-matrix in `contextual`.
- **Golden-dataset-tests** (`tests/golden/`): vaste set Nederlandse
  voorbeeld-teksten met ground-truth annotaties. Elke flavor draait ertegen,
  output wordt vergeleken op gedeelde invarianten (elk regex-detect moet
  in élke flavor voorkomen; recall-verschillen op NER mogen binnen
  bandbreedte).
- **Reden:** voorkomt stille drift tussen flavors en maakt recall/precision-
  verschillen zichtbaar bij elke PR.
- **Resource-consequentie:** CPU-runners draaien contract + classic + gliner-
  CPU; GPU of nightly-runner draait contextual + gliner-GPU.

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
- **Risk: `gliner` als current-default betekent dat `classic` qua recall
  zwakker zal ogen.** Dev-teams die nu werken verwachten GLiNER-output. →
  Mitigatie: default dev-compose draait `gliner`, productie-default wordt
  bewust per klant gekozen op basis van use-case.
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
   - `plugins.gliner.yaml` (huidige state onder nieuwe naam).
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
