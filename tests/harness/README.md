# Flavor test-harness

Container-gebaseerde tests voor de drie OpenAnonymiser flavors
(`classic`, `gpu`, `contextual`). Deze harness spint per flavor een
container op (via `docker compose` of `podman compose`) en draait de
bestaande httpx-tests + een golden-dataset-runner ertegen.

> **Scope:** deze skeleton test **classic** (= wat op `main` / `staging`
> draait) en **gpu** (= wat op `development` draait, zij het nog
> incompleet). `contextual` wordt toegevoegd wanneer de flavor-split-PR
> (`openspec/changes/split-into-3-flavors`) een `plugins.contextual.yaml`
> oplevert.

## Snel draaien

### Beide flavors tegelijk (aanbevolen)

Start classic (tag `:main`) én gpu (tag `:development`) parallel, run
alle harness-tests in één pytest-aanroep:

```bash
OPENANONYMISER_IMAGE_CLASSIC=ghcr.io/conductionnl/openanonymiser:main \
OPENANONYMISER_IMAGE_GPU=ghcr.io/conductionnl/openanonymiser:development \
  docker compose -f tests/harness/compose.yaml up -d
pytest tests/harness/ -v
docker compose -f tests/harness/compose.yaml down
```

Dit is de default-workflow: je krijgt per flavor een apart rapport in
dezelfde run en ziet verschillen side-by-side.

### Eén flavor tegelijk

Handig als je alleen één image wil valideren of resources beperkt zijn:

```bash
OPENANONYMISER_IMAGE_CLASSIC=ghcr.io/conductionnl/openanonymiser:main \
  docker compose -f tests/harness/compose.yaml up -d classic
pytest tests/harness/test_option_1_classic.py -v
docker compose -f tests/harness/compose.yaml down
```

Poort-mapping: classic → 8081, gpu → 8082. Tests die tegen een niet-
draaiende container aan praten, skippen automatisch.

## Golden dataset

Zie [`../golden/README.md`](../golden/README.md). De runner (`golden/runner.py`)
leest `dataset.jsonl`, stuurt elk voorbeeld naar `/api/v1/analyze`, en
produceert een rapport met precision/recall per entity-type.

## Wat test wat?

| Test-file | Tegen flavor | Harde assertions | Soft assertions |
|---|---|---|---|
| `test_option_1_classic.py` | classic | Alle regex-entities in golden-set gedetecteerd | NER-recall ≥ 0.8 op PERSON |
| `test_option_2_gpu.py` | gpu (dev) | Health + DTO-contract | Regex-entities: XFAIL tot flavor-split-PR landt (development heeft patterns uit) |

## CI

Deze harness is bewust **niet** onderdeel van de standaard `pytest` run
op CI (vereist container-runtime). Een aparte GitHub Actions workflow
`.github/workflows/harness.yml` (te maken) draait hem op een CPU-runner
voor classic en een GPU-runner voor gpu.

Tests zijn gemarkeerd met de `harness` pytest-marker en geskipt tenzij
`OPENANONYMISER_BASE_URL` gezet is of `--run-harness` wordt meegegeven.
