# Changelog

Alle belangrijke wijzigingen in dit project worden in dit bestand gedocumenteerd.

De opmaak is gebaseerd op [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) en dit project maakt gebruik van [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `docs/architecture/flavors.md` — stavaza + architecturele definitie van drie flavors (`classic`, `gpu`, `contextual`) met per flavor een expliciet deployment-model (self-contained / SaaS / SaaS+externe-deps)
- `docs/architecture/entity-contract.md` — entity-matrix per flavor als bron-van-waarheid
- `openspec/changes/split-into-3-flavors/` — proposal, design, tasks voor drie-smaken-split (ter review)

### Notes
- Versie-discrepantie gesignaleerd: CHANGELOG staat op 1.4.0, `src/api/main.py:45` staat op 1.3.0 — wordt bij merge van de flavor-split gesynct naar 1.5.0.
- De-facto branch→flavor-mapping gedocumenteerd: `main` en `staging` draaien al `classic`; `development` draait een incomplete `gpu` (regex uit). De flavor-split maakt deze mapping expliciet en repareert de gap op `development`.

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