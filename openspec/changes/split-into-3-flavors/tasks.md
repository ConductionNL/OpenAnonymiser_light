## 0. Voorafgaand — review & beslissen

- [ ] 0.1 Team-review op `docs/architecture/flavors.md` en `entity-contract.md`
- [ ] 0.2 Open vragen uit `flavors.md` §8 sluiten (naamgeving, default per omgeving, verifier-keuze, entity-matrix)
- [ ] 0.3 Versie-discrepantie afstemmen — bump naar 1.5.0 bij merge?

## 1. Plugin-configs splitsen

- [ ] 1.1 `src/api/config/plugins.classic.yaml` — SpaCy NER + alle pattern recognizers enabled, geen GLiNER. Komt overeen met huidige main/staging state.
- [ ] 1.2 `src/api/config/plugins.gpu.yaml` — transformer-NER (GLiNER default) enabled, pattern recognizers **ook enabled** (anders geen EMAIL/IBAN/etc. — is de huidige gap op development-branch).
- [ ] 1.3 `src/api/config/plugins.contextual.yaml` — SpaCy + patterns + verifier-plugin (transformer of llm) voor BSN/ID_NO
- [ ] 1.4 Verplaats huidige `src/api/plugins.yaml` of maak deze een symlink/kopie van default flavor (voorstel default: `classic`)
- [ ] 1.5 Update `plugin_loader.py` zodat default-pad flavor-aware is (fallback naar `classic` als `PLUGINS_CONFIG` niet gezet)

## 2. Code aanpassingen

- [ ] 2.1 `src/api/config.py`: `ALL_SUPPORTED_ENTITIES` wordt dynamisch uit geladen plugin-config (niet meer hardcoded)
- [ ] 2.2 `src/api/dtos.py`: optioneel `recognizer`-veld in `PIIEntity` (auditability)
- [ ] 2.3 `src/api/routers/text_analysis.py`: request-validatie voor `entities` tegen flavor-specifieke lijst (422 als niet gedekt)
- [ ] 2.4 `src/api/main.py:45`: versie-bump naar 1.5.0 (na beslissing 0.3)
- [ ] 2.5 Bouw `VerifierRecognizer`-wrapper voor contextual-flavor: neemt pattern/NER-kandidaten, vraagt LLM/transformer binaire classificatie, filtert false positives
- [ ] 2.6 Startup-log uitbreiden: welke flavor is geladen, welke entities ondersteund

## 3. Dependencies

- [ ] 3.1 `pyproject.toml`: `gliner` uit default-dependencies halen
- [ ] 3.2 `pyproject.toml`: `[project.optional-dependencies]` toevoegen — `classic = []`, `gpu = ["gliner>=0.1.13"]`, `contextual = ["transformers", "torch", ...]`
- [ ] 3.3 `uv sync --extra classic` smoke-test — moet werken zonder gliner/torch
- [ ] 3.4 Update `.env.example` — `PLUGINS_CONFIG`, `FLAVOR` env-vars documenteren

## 4. Docker

- [ ] 4.1 `Dockerfile.classic` — SpaCy model, geen gliner, geen torch
- [ ] 4.2 `Dockerfile.gpu` — transformer-NER model pre-download (GLiNER default), SpaCy model, CUDA-compatible base-image
- [ ] 4.3 `Dockerfile.contextual` — transformer model (mdeberta) pre-download OF LLM-API credentials via env (provider-afhankelijk)
- [ ] 4.4 Image-size meten per flavor, documenteren in `flavors.md` §6
- [ ] 4.5 Bandit-scan per image (per CLAUDE.md regel 4): `bandit -r src/ -ll -q` na build

## 5. CI

- [ ] 5.1 GitHub Actions workflow: contract-tests voor alle flavors op CPU-runner (geen echte engine-loading)
- [ ] 5.2 GitHub Actions workflow: `classic` engine-tests op CPU-runner
- [ ] 5.3 Nightly of label-triggered GPU-job voor `gpu` + `contextual` engine-tests
- [ ] 5.4 Image-build workflows per flavor (tag als `openanonymiser-<flavor>:<sha>`)
- [ ] 5.5 CI-check: PR die `src/api/utils/patterns.py` of `plugins.*.yaml` wijzigt moet ook `docs/architecture/entity-contract.md` diff hebben (guard tegen drift)

## 6. Tests — contract-laag

- [ ] 6.1 `tests/contract/conftest.py` — pytest-fixture die de API start met elke flavor (parametrize)
- [ ] 6.2 `tests/contract/test_api_shape.py` — assert HTTP-codes, DTO-shape voor `/analyze`, `/anonymize`, `/health`
- [ ] 6.3 `tests/contract/test_entity_validation.py` — assert 422 voor entities buiten flavor
- [ ] 6.4 `tests/contract/test_anonymization_strategies.py` — alle strategies (replace/redact/hash/mask) werken per flavor
- [ ] 6.5 `tests/contract/test_flavor_configs.py` — elke `plugins.<flavor>.yaml` is laadbaar, geen import-errors

## 7. Tests — per flavor

- [ ] 7.1 `tests/flavors/classic/` — pattern-overlap-resolutie, SpaCy NER-kwaliteit tegen mini-set
- [ ] 7.2 `tests/flavors/gpu/` — transformer-NER entity-mapping (GLiNER-specifiek nu, engine-agnostisch schrijven), custom-label-support
- [ ] 7.3 `tests/flavors/contextual/` — verifier confusion-matrix tegen gelabelde BSN/niet-BSN-voorbeelden (met mock LLM-provider)

## 8. Tests — cross-flavor / golden dataset

- [ ] 8.1 `tests/golden/dataset.jsonl` — vaste set Nederlandse teksten met ground-truth entity-spans (start: 20 voorbeelden)
- [ ] 8.2 `tests/golden/runner.py` — draait dataset door elke flavor, produceert per-flavor rapport (precision/recall/F1 per entity-type)
- [ ] 8.3 `tests/golden/test_invariants.py` — harde assertions: regex-entities (EMAIL, IBAN, BSN, etc.) moeten door ELKE flavor gedetecteerd worden
- [ ] 8.4 `tests/golden/test_regression_bands.py` — NER-recall per flavor binnen vooraf vastgelegde bandbreedtes (hard-fail op >X% drop)
- [ ] 8.5 Output van golden-run committen als `tests/golden/baseline.<flavor>.json` voor regressiecheck

## 9. Deployment (Helm + K8s)

- [ ] 9.1 `charts/openanonymiser/values.yaml`: `flavor: classic` default, per-flavor `resources`-presets
- [ ] 9.2 Deployment-template: selecteert juiste image-tag op basis van `flavor`
- [ ] 9.3 Helm dry-run per flavor: `helm template openanonymiser ./charts/openanonymiser --set flavor=<flavor>`
- [ ] 9.4 VRAAG aan gebruiker vóór `helm upgrade` op dev/acc/prod

## 10. Docs bijwerken

- [ ] 10.1 `README.md` — flavor-keuze in quickstart
- [ ] 10.2 `docs/01-getting-started.md` — installatie per flavor
- [ ] 10.3 `docs/03-configuration.md` — `PLUGINS_CONFIG`, `FLAVOR` documenteren
- [ ] 10.4 `docs/04-deployment.md` — per-flavor resource-profiel, image-tags
- [ ] 10.5 Google Doc (externe overview) inkorten, bovenaan link naar `docs/architecture/flavors.md` op main
- [ ] 10.6 CHANGELOG-entry onder 1.5.0

## 11. Smoke-tests na merge

- [ ] 11.1 Lokaal per flavor: `PLUGINS_CONFIG=src/api/config/plugins.<flavor>.yaml uv run api.py` → `/health` + `/analyze`
- [ ] 11.2 Docker per flavor: build, run, `/health`
- [ ] 11.3 Golden-dataset draaien: baseline-rapporten per flavor committen
- [ ] 11.4 Bandit per src-tree (onveranderd)
