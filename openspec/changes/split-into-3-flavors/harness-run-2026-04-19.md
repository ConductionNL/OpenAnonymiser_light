# Harness-run observations — 2026-04-19

Observaties uit een container-run van de flavor test-harness
(`feature/flavor-test-harness`) tegen de huidige productie- en
development-images, als input voor de review van dit openspec-change.

## Setup

- `classic` → `docker.io/mwest2020/openanonymiser-light:main` op :8081
- `gpu` → `docker.io/mwest2020/openanonymiser-light:dev` op :8082
- `pytest tests/harness/ -v` → `8 failed, 10 passed, 5 xpassed` in 8.81s

## Relevant voor `tasks.md`

### §1.1 — `plugins.classic.yaml` klopt niet met huidige main-state

`tasks.md` §1.1 stelt dat `classic` "overeenkomt met huidige main/staging
state: SpaCy NER + alle pattern recognizers enabled". De harness-run weerlegt
dit: `:main` detecteert **niet**:

- `CASE_NO` (recall 0.0)
- `IP_ADDRESS` (recall 0.0)
- `KVK_NUMBER` (recall 0.0)
- `LICENSE_PLATE` (recall 0.0)
- `PHONE_NUMBER` — partial (recall 0.5, één correct + één false positive)

Analyze-response op `:main` voor een tekst met alle vier entities:
`{"pii_entities": []}`.

**Consequentie voor §1.1:** `plugins.classic.yaml` kan niet simpelweg
"main-gedrag kopiëren" — die vier recognizers moeten expliciet opgenomen
én getest worden. Dit is óók nieuwe scope voor een eventuele hotfix op main
onafhankelijk van de flavor-split.

### §1.2 — `plugins.gpu.yaml` — patterns staan op dev al aan

`tasks.md` §1.2 stelt dat `development` momenteel "patterns uit" heeft; dit
zou de huidige gap op dev verklaren. De harness-run laat zien dat op `:dev`
5 regex-entity-tests met `xfail`-marker **xpassed** zijn
(`EMAIL`, `PHONE_NUMBER`, `IBAN`, `DATE_TIME`, `BSN`).

Plausibele verklaringen (te verifiëren vóór §1.2 gebouwd wordt):
1. `plugins.yaml` op dev heeft `enabled: false` per recognizer (zie
   `src/api/plugins.yaml` op `origin/development`) maar een code-pad
   overschrijft dat.
2. Presidio laadt pattern-recognizers onafhankelijk van plugins.yaml via
   een andere initialisatie-pad.
3. De `:dev`-image is uit een andere branch/config gebouwd dan
   `origin/development` suggereert.

**Consequentie voor §1.2:** check-stap toevoegen — voor je
`plugins.gpu.yaml` schrijft, bevestig eerst hoe patterns op `:dev` in
werking zijn ondanks `enabled: false` in de YAML.

### NER-recall onder aangenomen drempels (classic + gpu)

Op de huidige 14-voorbeeld golden-set:
- Classic `PERSON` 0.50 (harness-drempel 0.75), `ORGANIZATION` 0.00
  (drempel 0.50).
- GPU `PERSON` 0.50 (harness-drempel 0.85).

Dataset is klein (14 voorbeelden), dus harde conclusies te vroeg. Maar de
drempels in `test_option_{1,2}_*.py` zijn gekalibreerd op aannames, niet op
meetwaarden.

**Consequentie voor §7 / §8:** golden-dataset uitbreiden naar ≥20 entries
(conform §8.1) vóór de drempels geaccepteerd worden als regressie-signaal.
Tot die tijd: drempels loslaten of markeren als "indicatief".

## Niet in tasks.md maar wel te fixen

- `tests/harness/README.md` + `compose.yaml` verwijzen naar
  `ghcr.io/conductionnl/openanonymiser:{main,development}`. De werkelijke
  registry is `docker.io/mwest2020/openanonymiser-light:{main,dev}` (zie
  `.github/workflows/docker-build.yml` env `REGISTRY=docker.io`,
  `IMAGE_NAME=mwest2020/openanonymiser-light`). Kleine doc-fix op de
  harness-branch.
- De `xfail`-marker in `tests/harness/test_option_2_gpu.py::TestGoldenRegexInvariants`
  is niet meer geldig; kan weg zodra §1.2-verificatie klaar is.
