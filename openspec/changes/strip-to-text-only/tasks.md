## 1. Bestanden verwijderen

- [ ] 1.1 Verwijder `src/api/routers/documents.py`
- [ ] 1.2 Verwijder `src/api/crud.py`
- [ ] 1.3 Verwijder `src/api/database.py`
- [ ] 1.4 Verwijder `src/api/dependencies.py`
- [ ] 1.5 Verwijder `src/api/models.py`
- [ ] 1.6 Verwijder `src/api/utils/crypto.py`
- [ ] 1.7 Verwijder `src/api/utils/pdf_xmp.py`
- [ ] 1.8 Verwijder `src/api/utils/nlp/transformers_engine.py`
- [ ] 1.9 Verwijder `src/ui/` directory

## 2. Code aanpassen

- [ ] 2.1 `src/api/routers/__init__.py`: verwijder `documents_router` import en include
- [ ] 2.2 `src/api/dtos.py`: verwijder document-gerelateerde DTOs
- [ ] 2.3 `src/api/config.py`: verwijder DB/crypto/PDF settings
- [ ] 2.4 `src/api/utils/nlp/loader.py`: verwijder transformers branch

## 3. Dependencies

- [ ] 3.1 `pyproject.toml`: verwijder pikepdf, pymupdf, pycryptodome, sqlalchemy, transformers, torch
- [ ] 3.2 `uv sync` draaien → nieuwe uv.lock genereren

## 4. Dockerfile vereenvoudigen

- [ ] 4.1 Verwijder transformers model pre-download layer (wietsedv/bert-base-dutch-cased-ner)
- [ ] 4.2 Verwijder `TRANSFORMERS_CACHE` / `HF_HOME` ENV vars
- [ ] 4.3 Verwijder `nvidia-*` gerelateerde aannames (zijn al indirect via torch)

## 5. Helm chart aanpassen

- [ ] 5.1 `charts/openanonymiser/values.yaml`: `persistence.enabled: false` default
- [ ] 5.2 `charts/openanonymiser/templates/pvc.yaml`: wrap in `{{- if .Values.persistence.enabled }}`
- [ ] 5.3 `charts/openanonymiser/templates/deployment.yaml`: verwijder volumeMounts/volumes voor DB/files als PVC disabled
- [ ] 5.4 Verwijder DB/crypto env vars uit values.yaml (of maak optional)

## 6. Testen

- [ ] 6.1 Lokaal: `source .venv/bin/activate && uv run api.py` → `/health` smoke test
- [ ] 6.2 Lokaal: `POST /api/v1/analyze` met testtekst
- [ ] 6.3 Docker: `docker build -t openanonymiser-light .` succesvol
- [ ] 6.4 Docker: `docker run -p 8080:8080 openanonymiser-light` → `/health` smoke test
- [ ] 6.5 Helm: `helm template openanonymiser ./charts/openanonymiser` zonder errors
