# text-only-api

Slanke presidio + SpaCy REST API voor PII detectie en anonimisering van Nederlandse tekst.

---

### Requirement: Health endpoint

De API SHALL een `GET /api/v1/health` endpoint bieden dat `{"ping": "pong"}` retourneert zonder authenticatie.

#### Scenario: Health check

WHEN een client `GET /api/v1/health` aanroept
THEN retourneert de API `200 OK` met body `{"ping": "pong"}`

---

### Requirement: Tekst analyseren

De API SHALL een `POST /api/v1/analyze` endpoint bieden.

#### Scenario: Analyze met default engine

WHEN een client `{"text": "Jan Janssen woont in Amsterdam"}` POST naar `/api/v1/analyze`
THEN retourneert de API een lijst van gedetecteerde PII entities met `entity_type`, `text`, `start`, `end`, `score`

#### Scenario: Analyze met expliciete entities filter

WHEN een client `{"text": "...", "entities": ["PERSON", "PHONE_NUMBER"]}` POST
THEN retourneert de API alleen entiteiten van de gevraagde types

---

### Requirement: Tekst anonimiseren

De API SHALL een `POST /api/v1/anonymize` endpoint bieden.

#### Scenario: Anonymize tekst

WHEN een client `{"text": "Jan Janssen, tel: 0612345678"}` POST naar `/api/v1/anonymize`
THEN retourneert de API `original_text`, `anonymized_text` (met `<PERSON>`, `<PHONE_NUMBER>` placeholders), en `entities_found`

---

### Requirement: NLP engines

De API SHALL SpaCy (`nl_core_news_lg` in dev, `nl_core_news_md` in productie) gebruiken voor NER.
De API SHALL GEEN Transformers/torch dependency hebben.

#### Scenario: SpaCy engine beschikbaar

WHEN de API start
THEN laadt de SpaCy engine zonder errors en logt het model-naam

---

### Requirement: Pattern recognizers

De API SHALL de volgende NL-specifieke pattern recognizers actief hebben:
`PHONE_NUMBER`, `IBAN`, `BSN`, `DATE_TIME`, `EMAIL`, `ID_NO`, `DRIVERS_LICENSE`, `CASE_NO`

---

### Requirement: Stateless deployment

De API SHALL geen persistente opslag vereisen (geen SQLite, geen file-upload, geen crypto keys voor PDF).

#### Scenario: Pod restart

WHEN een Kubernetes pod herstart
THEN is de API direct beschikbaar zonder data-migratie of volume-mounts
