# Changelog

Alle belangrijke wijzigingen in dit project worden in dit bestand gedocumenteerd.

De opmaak is gebaseerd op [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) en dit project maakt gebruik van [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Build pipeline gesplitst in `classic` + `gpu` flavors** (`Dockerfile.classic` / `Dockerfile.gpu`, beide multi-stage met `python:3.12.11-slim-bookworm` runtime). Plugin-config-selectie via `PLUGINS_CONFIG` env-var.
- `pyproject.toml` extras-split: `gliner` verhuisd van base `dependencies` naar `[project.optional-dependencies].gpu`. Gevolg: classic-image trekt geen torch / CUDA / triton mee → **6 GB → 1.1 GB**.
- `src/api/plugins.classic.yaml` — alle Dutch-PII pattern recognizers `enabled: true`, geen GLiNER. Voor sidecar / Nextcloud / on-prem appliance.
- `src/api/plugins.gpu.yaml` — huidige `development`-state geconserveerd: GLiNER + spaCy + alleen `MACAddressRecognizer`. Pattern-set wordt heringeschakeld in een vervolg-PR (zie design.md decision 4).
- `.github/workflows/docker-build.yml` matrix — bouwt `classic` en `gpu` parallel per push. Tag-strategie: `:{tier}-{flavor}` plus default-aliases `:latest` (classic), `:acc` (classic), `:dev` (gpu — bewaart huidig dev-cluster-gedrag).
- README: nieuwe Flavors-sectie met build-commando's en link naar `docs/architecture/flavors.md`.
- `.env.example`: `PLUGINS_CONFIG` voorbeeld + uitleg.

### Security
- **Dependabot CVE-fix sweep** — `uv lock --upgrade` ruimt 21 alerts op default-branch op (8 HIGH, 11 MEDIUM, 2 LOW). Belangrijkste bumps: starlette 0.46→1.0, uvicorn 0.34→0.46, urllib3 2.4→2.6.3, orjson 3.9→3.11.6, python-multipart 0.0.20→0.0.22, ujson verwijderd (nergens meer een directe consumer). Alle 21 tests pass tegen draaiende API; geen regressie.

### Changed
- **spaCy `nl_core_news_lg` overal** — lokaal venv, container, K8s. Was: lg lokaal, md in container. Beleid bijgesteld voor consistentie. `Dockerfile.{classic,gpu}` zetten `ENV DEFAULT_SPACY_MODEL=nl_core_news_lg`. Plugin yaml's defaulten nu op `${DEFAULT_SPACY_MODEL:-nl_core_news_lg}`. CLAUDE.md spaCy-sectie bijgewerkt.
- `.github/workflows/docker-build.yml` test-job: `DEFAULT_SPACY_MODEL=nl_core_news_lg` (was md). Aparte md-pip-install-step verwijderd; `uv sync` installeert lg uit pyproject hard dep.
- Lokale dev-pad voor wie GPU-flavor wil testen: `uv sync --extra gpu` (was: gliner standaard mee). Documenteer in README.

### Notes
- `Dockerfile` (single-stage) is hernoemd naar `Dockerfile.gpu` en herschreven als multi-stage. Multi-stage haalt `uv` + build-tools uit de runtime image.
- `plugins.yaml` blijft als default fallback voor lokale dev (`uv run api.py` zonder `PLUGINS_CONFIG`); geen breaking change voor bestaande lokale workflows zolang `uv sync` zonder extras gedraaid wordt.
- `k8s/overlays/{dev,acc,prod}/config.env` bijgewerkt naar `DEFAULT_SPACY_MODEL=nl_core_news_lg` (consistent met spaCy-overal-lg beleid). Image-tag in deze overlays blijft ongewijzigd (`:dev`/`:acc`/`:latest` via alias) — de switch naar `:{tier}-classic` is een vervolg-PR.
- Geen andere k8s overlay-changes in deze PR: dev-overlay blijft `:dev` pullen (= gpu via alias) zodat huidig cluster-gedrag stabiel is.
- `.claude/file-write-allowlist` toegevoegd: project-scoped carve-out voor de globale `.env`-write-block, specifiek voor `k8s/overlays/*/config.env` (configmap-inputs, geen secrets).
- CI: PR-builds geactiveerd voor PR's tegen `development` en `staging` (`pull_request: branches:` uitgebreid). Build-step blijft `push: false` voor PR's, dus geen registry-bijwerken — alleen Dockerfile-validatie vóór merge.
- CI: `feature-testing.yml` en `docker-build.yml` test-job draaien nu `uv sync ... --extra gpu`. Default `plugins.yaml` heeft GLiNER nog op enabled (legacy dev-state); zonder extra crashte API-startup na de pyproject extras-split.
- CI: **Trivy image-scan toegevoegd** (`aquasecurity/trivy-action@v0.36.0`) als gate vóór registry push. Build → load naar runner → scan → pas pushen als groen. Severity HIGH+CRITICAL, `ignore-unfixed: true`. Vult het gat dat bandit (source) en dependabot (pyproject) niet dekken: OS-packages en Python-wheel-binaries in de gebouwde image.
- **Docker Hub namespace-migratie** `mwest2020/openanonymiser-light` → `conductiondeploy/openanonymiser-light`. Eigenaarschap verschuift van persoonlijk account naar organisatie-Service-Account; voorkomt single-point-of-failure rond persoonlijke token-rotatie. Aangeraakt: `.github/workflows/{docker-build,retag-image}.yml`, `k8s/base/deployment.yaml`, `k8s/overlays/*/kustomization.yaml`. Repo-secrets `DOCKER_USERNAME` + `DOCKER_PASSWORD` behouden dezelfde naam — vul ze met SA-credentials via `bash scripts/setup-dockerhub-secrets.sh` (interactieve prompt, geen copy-paste).
- **K8s overlays expliciet op classic-tags**: `dev` → `dev-classic`, `acc` → `acc-classic`, prod → `classic-latest`. Was: leunen op aliassen (`:dev`=gpu, `:acc`=classic, `:latest`=classic). Reden: dev-cluster heeft geen GPU-pool → moet classic draaien (memory: cluster_no_gpu); staging/main draaiden via alias al classic, nu gewoon expliciet. Aliassen in de workflow blijven bestaan (geen consument meer, maar onschuldig — kan in vervolg-cleanup eruit).
- `contextual` flavor (verifier-architectuur) blijft uit scope tot de verifier-implementatie er is.

- `docs/architecture/flavors.md` — stavaza + architecturele definitie van drie flavors (`classic`, `gpu`, `contextual`) met per flavor een expliciet deployment-model (self-contained / SaaS / SaaS+externe-deps)
- `docs/architecture/entity-contract.md` — entity-matrix per flavor als bron-van-waarheid
- `openspec/changes/split-into-3-flavors/` — proposal, design, tasks voor drie-smaken-split (ter review)

### Notes
- Versie-discrepantie gesignaleerd: CHANGELOG staat op 1.4.0, `src/api/main.py:45` staat op 1.3.0 — wordt bij merge van de flavor-split gesynct naar 1.5.0.
- De-facto branch→flavor-mapping gedocumenteerd: `main` en `staging` draaien al `classic`; `development` draait een incomplete `gpu` (regex uit). De flavor-split maakt deze mapping expliciet en repareert de gap op `development`.
- `tests/harness/` — container-gebaseerde test-harness per flavor. Spint via `compose.yaml` een OpenAnonymiser-container op (classic of gpu) en draait tests tegen de draaiende API. Skipt automatisch als de container niet bereikbaar is, dus veilig in standaard CI.
- `tests/golden/` — golden dataset (14 Nederlandse voorbeelden, 17 entity-spans) + runner met per-entity precision/recall/F1-rapportage.
- `tests/harness/test_option_1_classic.py` — harde invarianten: elk regex-entity in golden-set moet 100 % recall halen op classic. Soft NER-bands voor PERSON/LOCATION/ORGANIZATION.
- `tests/harness/test_option_2_gpu.py` — DTO-contract + NER-bands. Regex-assertions `xfail`-gemarkeerd tot flavor-split-PR landt (development heeft nu patterns disabled).

### Notes
- Deze branch werkt parallel aan `feature/3-flavors-design` (docs) en `openspec/changes/split-into-3-flavors` (architectuur-proposal). Test-harness merget idealiter eerst en dient dan als validatie-gate voor de flavor-split-PR.

## [1.4.1] - 2026-04-17

### Added
- Benchmark setup uitgebreid met 
  - Multi entity zinnen dataset
  - Visualisatie (confusion matrixen) 
  - Genereer html reports (TP/FN/FP) voor benchmark resultaten
  - Uitgebreide errors voor analyseren benchmark resultaten
- Bug fixes in custom pattern recognizers
- Presidio context enhancer logic toegevoegd (nog niet getest), kan disabled/enabled worden in `plugins.yaml`
- GLiNER entiteiten meegenomen bij de logica voor het filteren van span-overlaps
- Meer spaCy NER entiteiten toegevoegd om te herkennen

## [1.4.0] - 2026-04-03

### Changed
- Presidio GLiNER Recognizer toegevoegd als module
- Custom pattern recognizers (BSN/IBAN/etc.) op false gezet
- Skip pattern recognizers tests

## [1.3.0] - 2026-03-02

### Removed
- Document endpoints (`/documents/upload`, `/documents/{id}/anonymize`, `/documents/{id}/download`)
- SQLite database, file storage, crypto layer
- Transformers/HuggingFace NER engine (torch, transformers, wietsedv/bert-base-dutch-cased-finetuned-sonar-neTagger)
- React UI (`src/ui/`)
- PDF-processing (`pikepdf`, `pymupdf`)

### Changed
- Deployment is nu volledig stateless (`persistence.enabled: false` in Helm)
- SpaCy `nl_core_news_md` gebakken in Docker image (geen runtime download)
- Docs volledig herschreven naar `docs/` (getting-started, api-reference, configuration, deployment)

## [1.2.0] - 2025-01-30

### Added
- String-based endpoints: `/api/v1/analyze` en `/api/v1/anonymize`
- Consistente response format tussen document en string endpoints
- Pre-download van transformers models tijdens Docker build

### Fixed
- Gescheiden NLP engines voor custom analyse vs Presidio patterns
- Verbeterde architectuur met modulaire text analyzer
- Performance optimalisatie door model pre-loading

### Changed
- Docker build proces geoptimaliseerd voor snellere startup
- Deployment setup met staging/production branches
- ArgoCD configuratie voor geautomatiseerde deployments

### Technical
- Presidio framework geïntegreerd voor PII detectie
- Dual NLP engine support (SpaCy + Transformers)
- Kubernetes deployment met Helm charts

## [1.1.0] - 2025-01-29

### Added
- Multi-environment setup (staging/production)
- GitHub Actions workflows voor automated deployments
- Comprehensive deployment guides

### Fixed
- GitOps workflow vereenvoudigd
- Docker image tagging gestandaardiseerd

## [1.0.8] - 2025-01-28

### Added
- Externe toegankelijkheid via ingress
- SSL certificaten met Let's Encrypt
- Production-ready deployment

## [0.0.1] - 2025-05-09

### Added
- Herziening van de Presidio-Nl api v1
- Projectafspraken en opbouw Python
- Testsuite
- PII-detectie voor:
    * naam
    * e-mailadressen
    * telefoonnummers
    * beperkte lokatienamen
- IBAN recognizer generiek gemaakt en getest
- Testscript toegevoegd (`test_iban.py`)
- Voorbereiding voor nieuwe aanpak locatieherkenning 