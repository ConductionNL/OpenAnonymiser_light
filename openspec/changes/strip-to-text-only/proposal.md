## Why

De huidige codebase bevat een volledige document-pipeline (PDF upload, SQLite, crypto, transformers/torch) die niet nodig is voor de kern-usecase: tekst anonimiseren via presidio + regex. Het verwijderen van deze lagen reduceert de image-size drastisch (~2GB → ~500MB), vermindert aanvalsoppervlak, en maakt de straat (lokaal → Docker → Helm) sneller te valideren.

## What Changes

- **BREAKING** Verwijder document endpoints (`/documents/*`): upload, anonymize, deanonymize, metadata, download
- Verwijder SQLite database laag (models, crud, dependencies, database.py)
- Verwijder crypto utilities (AES-encryptie van PDF metadata)
- Verwijder PDF processing (pdf_xmp.py, PyMuPDF, pikepdf)
- Verwijder Transformers/torch NLP engine (transformers_engine.py, ~1.5GB aan CUDA packages)
- Verwijder frontend (src/ui/)
- Vereenvoudig Dockerfile: geen transformers model pre-download layer
- Vereenvoudig Helm chart: geen PVC vereist (geen bestanden/DB op disk)
- Behoud: presidio AnalyzerEngine, patterns.py recognizers, SpaCy nl_core_news_lg NER
- Behoud: `/api/v1/analyze` en `/api/v1/anonymize` text endpoints
- Behoud: `/api/v1/health` endpoint

## Capabilities

### New Capabilities
- `text-only-api`: Slanke tekst-analyse en anonimisering API met alleen presidio patterns + SpaCy NER, zonder document/storage laag

### Modified Capabilities
- (geen – de text-analyse endpoints wijzigen niet qua gedrag, enkel de infrastructuur eromheen)

## Impact

- **Verwijderde files**: `documents.py`, `crud.py`, `database.py`, `dependencies.py`, `models.py`, `crypto.py`, `pdf_xmp.py`, `transformers_engine.py`, `src/ui/`
- **Gewijzigde files**: `pyproject.toml`, `uv.lock`, `Dockerfile`, `charts/openanonymiser/values.yaml`, `charts/openanonymiser/templates/pvc.yaml`, `src/api/routers/__init__.py`, `src/api/config.py`, `src/api/dtos.py`
- **Dependencies verwijderd**: pikepdf, pymupdf, pycryptodome, sqlalchemy, transformers, torch (+ alle NVIDIA CUDA packages)
- **Image size**: geschat van ~2.5GB naar ~600MB
