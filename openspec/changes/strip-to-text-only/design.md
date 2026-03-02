## Context

OpenAnonymiser draait momenteel als een full-stack API met twee lagen:
1. **Text layer**: presidio + SpaCy + patterns voor NER/regex op platte tekst
2. **Document layer**: PDF upload, SQLite opslag, AES crypto, PyMuPDF/pikepdf rendering

De document-laag brengt ~1.8GB extra dependencies mee (torch, CUDA packages, pikepdf, pymupdf) en vereist persistent storage in Kubernetes. Voor de validatie van de kern-functionaliteit (PII detectie/anonimisering) is alleen de text layer nodig.

## Goals / Non-Goals

**Goals:**
- Slanke API met alleen `/analyze` en `/anonymize` text endpoints
- Docker image < 700MB (t.o.v. ~2.5GB)
- Stateless deployment: geen PVC nodig in Kubernetes
- Snelle lokale dev-loop: `uv run api.py` zonder 825MB torch download

**Non-Goals:**
- PDF verwerking (apart service of toekomstige feature)
- UI (valt buiten scope van deze API-service)
- Transformers NLP engine (kan later als opt-in worden herintroduceerd)

## Decisions

### 1. Verwijder Transformers engine volledig
- **Keuze**: Geen `transformers_engine.py`, geen torch, geen CUDA packages
- **Reden**: SpaCy `nl_core_news_lg` biedt voldoende NER kwaliteit voor Dutch NLP; transformers voegt ~1.5GB toe aan het image
- **Alternatief overwogen**: Optioneel houden via `[tool.uv.sources]` extra-group — te complex voor nu

### 2. Verwijder document router volledig (geen deprecation endpoint)
- **Keuze**: Hard remove, geen 410 Gone stub
- **Reden**: Geen bestaande clients in production die deze light-versie verwachten; de volledige versie blijft bestaan

### 3. Config.py vereenvoudigen maar niet herstructureren
- **Keuze**: Verwijder DB/crypto/PDF settings, behoud `Settings`-klasse structuur
- **Reden**: Minimale diff, makkelijker te reviewen

### 4. Helm chart: PVC optioneel maken (niet verwijderen)
- **Keuze**: `persistence.enabled: false` default in values.yaml, PVC template blijft bestaan maar rendert niet
- **Reden**: Future-proof; als document-laag ooit terugkomt kan PVC worden ingeschakeld

### 5. `nl_core_news_lg` in pyproject.toml, `nl_core_news_md` in Dockerfile
- **Keuze**: Behoud huidige split (lg voor dev, md voor productie image)
- **Reden**: Dit was al zo; config.py `DEFAULT_SPACY_MODEL` bepaalt runtime welk model geladen wordt

## Risks / Trade-offs

- **Risk**: SpaCy-only NER mist soms namen in complexe zinnen → Mitigatie: dit was al het geval; transformers was opt-in
- **Risk**: `uv.lock` bevat nu verwijderde deps tot na `uv lock` → Mitigatie: direct `uv sync` draaien na pyproject.toml wijziging

## Migration Plan

1. Verwijder bestanden (documenten-laag)
2. Update pyproject.toml + run `uv sync` → nieuwe uv.lock
3. Update Dockerfile
4. Update Helm chart values
5. Lokaal testen: `uv run api.py` → smoke test `/health` + `/analyze`
6. Docker build + smoke test
7. Helm dry-run: `helm template` validatie
