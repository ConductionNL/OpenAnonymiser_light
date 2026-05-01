# Benchmarks – PII-detectie evaluatie

Benchmark- en evaluatieuitrusting voor Dutch PII-detectie in OpenAnonymiser. Meet precision, recall en F1-score per entiteitstype met karakter-span IoU matching.

## Overzicht

De benchmark pipeline evalueert PII (Personally Identifiable Information) detectie door:

1. **Gelabelde testdata** inladen (JSON met ground-truth entity spans)
2. **PII-detectie** uitvoeren via de Presidio analyzer (pattern recognizers + SpaCy NER)
3. **Span matching** met Intersection-over-Union (IoU) — minimaal 50% overlap standaard
4. **Label mapping** toepassen om dataset-labels te mappen op pipeline-labels
5. **Metriek berekening** per entiteitstype: True Positives, False Positives, False Negatives → Precision/Recall/F1
6. **Visualisaties genereren**: confusion matrix, per-entity metrics, error breakdown
7. **Drempels controleren**: optionele CI/CD validatie met minimale P/R vereisten

### Waarom IoU-matching?

Character-level IoU matching is betrouwbaarder dan token-based matching voor irregular Nederlandse tekst. Voorbeeld:
- Ground truth: `"Jantje Jansen"` (chars 0-13)
- Prediction: `"Jansen"` (chars 8-13)
- IoU = 5 overlapping chars / 13 total chars union = 0.38 (misses met standaard 0.5 threshold)

## Huidige pipeline configuratie

De standaard benchmark configuratie gebruikt **SpaCy NER + 13 custom pattern recognizers + Context Enhancer**.

### plugins.yaml

```yaml
ner:
  type: spacy
  model: ${DEFAULT_SPACY_MODEL:-nl_core_news_lg}
  entities: [LOCATION, MONEY, NORP, ORGANIZATION, PERSON]
  ner_strength: 0.85
  enabled: true

context_aware_enhancer:
  enabled: true
  context_similarity_factor: 0.35
  min_score_with_context_similarity: 0.4

recognizers:
  - name: DutchPhoneNumberRecognizer
    type: pattern
    enabled: true
  - name: DutchIBANRecognizer
    type: pattern
    enabled: true
  # ... (13 pattern recognizers totaal)
```

**Belangrijke configuratiekeuzes:**

| Keuze | Reden |
|-------|-------|
| DATE niet in SpaCy entities | SpaCy wint op score (0.85 > 0.50) van DutchDateRecognizer en hallucineert dates op niet-date tokens (nummers, IBAN's). DutchDateRecognizer is nu enige bron voor DATE. |
| Context Enhancer aan | Essentieel voor DRIVERS_LICENSE en KVK_NUMBER — hun regex base scores (0.01) vallen zonder CE onder de eval threshold (0.4). |
| GLiNER uit | Momenteel disabled; heeft onopgeloste problemen met PHONE_NUMBER (0% recall). |

### Label maps

Niet elke pipeline-configuratie ondersteunt dezelfde entity types. Label maps mappen dataset-labels naar pipeline-labels en sluiten niet-ondersteunde types uit van evaluatie.

Beschikbare maps in `benchmarks/label_maps/`:
- **`spacy_patterns.yaml`** — SpaCy NER + pattern recognizers (sluit niet-ondersteunde types uit)
- **`gliner_patterns.yaml`** — GLiNER + pattern recognizers (identity map, alles ondersteund)

Gebruik `--label-map` om een map mee te geven:
```bash
uv run benchmarks/evaluate.py --label-map benchmarks/label_maps/spacy_patterns.yaml
```

## Snelstart

### SpaCy + patterns (standaard)
```bash
uv run benchmarks/evaluate.py \
  --data benchmarks/data/dutch_generated_dataset.json \
  --label-map benchmarks/label_maps/spacy_patterns.yaml
```

### Met visualisaties en error analyse
```bash
uv run benchmarks/evaluate.py \
  --data benchmarks/data/dutch_generated_dataset.json \
  --label-map benchmarks/label_maps/spacy_patterns.yaml \
  --plot \
  --html-report \
  --show-errors \
  --output-dir benchmarks/output/my_run
```

Genereert in de output directory:
- `plots/confusion_matrix.html` — Interactive heatmap (ground truth vs predicted)
- `plots/metrics.html` — Bar chart met P/R/F1 per entity type
- `plots/error_distribution.html` — False Positives/Negatives breakdown
- `report.html` — Single-page HTML report met alle metrics

## Alle opties

| Optie | Type | Standaard | Beschrijving |
|-------|------|-----------|--------------|
| `--data` | path | `benchmarks/data/dutch_generated_dataset.json` | Pad naar gelabelde testdata (JSON) |
| `--thresholds` | path | `benchmarks/thresholds.yaml` | Pad naar drempelwaarden (YAML) |
| `--label-map` | path | geen | YAML label mapping (dataset→pipeline). Niet-gemapte labels worden uitgesloten. |
| `--score-threshold` | float | `0.4` | Minimum Presidio confidence score (0.0-1.0) |
| `--iou-threshold` | float | `0.5` | Minimum IoU voor span match als "correct" (0.0-1.0) |
| `--fail-on-threshold` | flag | false | Exit code 1 als drempel niet gehaald (voor CI) |
| `--show-errors` | flag | false | Print false positives, false negatives, partial matches |
| `--plot` | flag | false | Genereer visualisatie plots (confusion matrix, metrics, errors) |
| `--plot-format` | choice | `html` | Plot format: `html` (interactief), `png` (statisch), `both` |
| `--html-report` | flag | false | Genereer single-page HTML report met alle data en plots |
| `--output-dir` | path | `benchmarks/output/eval_run` | Directory waar plots en reports opgeslagen worden |
| `--entities` | string | None | Kommagescheiden entity types: `"PERSON,EMAIL,BSN"` (uppercase) |

## Laatste benchmark resultaten

**SpaCy (`nl_core_news_lg`) + patterns + Context Enhancer** op `dutch_generated_dataset.json` (491 zinnen na label-map filtering):

```
Entity                Precision   Recall       F1    TP   FP   FN
--------------------------------------------------------------------------------
BSN                        1.00     1.00     1.00    51    0    0
CASE_NO                    0.97     1.00     0.98    56    2    0
DATE                       1.00     1.00     1.00   227    0    0
DRIVERS_LICENSE            1.00     1.00     1.00    50    0    0
EMAIL                      1.00     0.96     0.98    74    0    3
IBAN                       1.00     1.00     1.00    51    0    0
ID_NO                      1.00     1.00     1.00    50    0    0
IP_ADDRESS                 1.00     1.00     1.00    73    0    0
KVK_NUMBER                 1.00     1.00     1.00    65    0    0
LICENSE_PLATE              0.93     1.00     0.97    69    5    0
LOCATION                   0.79     0.78     0.79   273   72   76
MAC_ADDRESS                1.00     1.00     1.00    50    0    0
MONEY                      0.00     0.00     0.00     0    0   52
NORP                       0.85     0.66     0.74    51    9   26
ORGANIZATION               0.35     0.49     0.41    67  127   69
PERSON                     0.83     0.90     0.86   330   68   38
PHONE_NUMBER               0.89     1.00     0.94    50    6    0
POSTCODE                   0.99     1.00     1.00   114    1    0
VAT_NUMBER                 1.00     1.00     1.00    50    0    0
```

**Observaties:**
- Alle pattern-gebaseerde entiteiten scoren (nagenoeg) perfect (BSN, CASE_NO, DATE, EMAIL, IBAN, etc.)
- DRIVERS_LICENSE en KVK_NUMBER halen 100% dankzij Context Enhancer (zonder CE: 0%)
- MONEY heeft geen recognizer en scoort 0% — SpaCy MONEY is te onbetrouwbaar voor Nederlandse valuta-notatie
- ORGANIZATION en LOCATION zijn zwak — inherente SpaCy NER limitatie op gesynthetiseerde data
- NORP recall (66%) wordt beperkt door SpaCy's dekking van Nederlandse nationaliteiten/groeperingen

## Gebruik voorbeelden

### 1. Threshold validation (CI/CD mode)
```bash
uv run benchmarks/evaluate.py \
  --label-map benchmarks/label_maps/spacy_patterns.yaml \
  --fail-on-threshold
```

Exit codes:
- **0** = alle drempels gehaald
- **1** = een of meer drempels niet gehaald (als `--fail-on-threshold`)
- **2** = config/data fout

### 2. Specifieke entiteiten debuggen
```bash
uv run benchmarks/evaluate.py \
  --entities "PHONE_NUMBER,KVK_NUMBER" \
  --show-errors \
  --plot
```

### 3. Strengere matching (higher IoU requirement)
```bash
uv run benchmarks/evaluate.py \
  --iou-threshold 0.75 \
  --show-errors
```

### 4. Custom dataset en output folder
```bash
uv run benchmarks/evaluate.py \
  --data benchmarks/data/dutch_pii_sentences.json \
  --output-dir benchmarks/output/eval_custom_v1 \
  --plot --html-report --show-errors
```

## Testdata

### Beschikbare datasets

| Dataset | Zinnen | Beschrijving |
|---------|--------|--------------|
| `dutch_generated_dataset.json` | 534 | Primair — gesynthetiseerd multi-entity (19 entity types) |
| `dutch_edge_cases_dataset.json` | — | Edge cases voor grensgevallen |
| `dutch_pii_sentences.json` | klein | Legacy, enkele entiteiten per zin |
| `dutch_synth_multi_entity_dataset.json` | 48 | Legacy multi-entity (246 spans) |

### Dataset structuur

```json
[
  {
    "full_text": "Mijn burgerservicenummer is 987654329 en mijn email: john@example.com",
    "spans": [
      {
        "entity_type": "BSN",
        "entity_value": "987654329",
        "start_position": 27,
        "end_position": 36
      },
      {
        "entity_type": "EMAIL",
        "entity_value": "john@example.com",
        "start_position": 54,
        "end_position": 70
      }
    ]
  }
]
```

**Regels:**
- `start_position` en `end_position` zijn 0-gebaseerde karakter-indexen
- `entity_value` moet exact gelijk zijn aan `full_text[start:end]`
- Test positie met `text[start:end]` voordat je de JSON submitteert

## Drempels (thresholds.yaml)

Optionele minimale P/R vereisten per entiteit voor CI/CD:

```yaml
PERSON:
  precision: 0.90
  recall: 0.85

EMAIL:
  precision: 1.0
  recall: 1.0

BSN:
  precision: 1.0
  recall: 1.0

PHONE_NUMBER:
  precision: 0.85
  recall: 0.90

# Entities niet vermeld = geen vereiste (0.0)
```

Standaard: alle drempels = 0.0 (geen UI/CD checks).

Na succesvolle run:
```bash
# Valideer tegen drempels
uv run benchmarks/evaluate.py --fail-on-threshold
```

## Output begrijpen

### Tabel (console)
```
Entity                Precision    Recall       F1     TP   FP   FN  Status
─────────────────────────────────────────────────────────────────────────────
BSN                        1.00      1.00     1.00      6    0    0  OK
EMAIL                      1.00      1.00     1.00      9    0    0  OK
PHONE_NUMBER               0.78      1.00     0.88      7    2    0  OK (! FP=2)
KVK_NUMBER                 0.70      1.00     0.82      7    3    0  FAIL (min p=0.95 r=0.90)
```

**Metriek-uitleg:**
- **TP** (True Positives) = Correct gedetecteerd
- **FP** (False Positives) = Fout gedetecteerd (niet in ground truth)
- **FN** (False Negatives) = Gemist (was in ground truth, model miste het)
- **Precision** = TP / (TP + FP) — hoe betrouwbaar zijn detecties?
- **Recall** = TP / (TP + FN) — hoeveel entiteiten worden gevonden?
- **F1** = 2 × (P × R) / (P + R) — balans tussen precision en recall; straft eenzijdig hoge P of R af

### Confusion Matrix (HTML)

Rijen = Ground Truth entity types  
Kolommen = Predicted entity types  
Diagonaal = Correct predictions (hoog gewenst)  
Off-diagonal = Misclassifications

Voorbeeld: EMAIL row:
```
EMAIL | 0 | 0 | 0 | 0 | 9 | 0 | 0 | ...
```
→ Alle 9 emails correct geclassificeerd, geen false positives/negatives.

### Error Reports (console)

Met `--show-errors`:

```
❌ False Positives (modeldetecteerde iets wat niet klopt):
────────────────────────────────────────────────────────────
  PHONE_NUMBER (2 total):
    • '0612345678'
      Context: ...rood de nummer 0612345678 op...
    • '003104-567890'
      Context: ...faxnummer 003104-567890 niet...

⚠️  False Negatives (model miste deze):
────────────────────────────────────────────────────────────
  KVK_NUMBER (2 total):
    • '12345678'
      Context: ...inschrijving KVK 12345678 bij...

📊 Partial Matches (te laag IoU):
───────────────────────────────────
  PERSON:
    Predicted:    'Jansen'
    Ground-truth: 'Jantje Jansen'
    IoU: 0.38
```

## Code structuur

```
benchmarks/
├── README.md                         # Dit bestand
├── evaluate.py                       # CLI entry point (click decorators)
├── evaluator.py                      # CustomEvaluator: IoU matching + metrics
├── plotter.py                        # EvaluationPlotter: matplotlib + plotly
├── generate_dataset.py               # Dataset generator (Faker-based)
├── validate_dataset.py               # Dataset validatie (span-checks)
├── thresholds.yaml                   # Optionele P/R drempels per entity
├── label_maps/
│   ├── spacy_patterns.yaml           # Label map: SpaCy NER + pattern recognizers
│   └── gliner_patterns.yaml          # Label map: GLiNER + pattern recognizers
├── data/
│   ├── dutch_generated_dataset.json  # Primair — 491 zinnen, 2262 spans, 23 entity types
│   ├── dutch_edge_cases_dataset.json # Edge cases — 135 zinnen, 264 spans, 23 entity types
│   └── generators/
│       ├── __init__.py
│       ├── edge_cases.py             # Edge case generatie logica
│       ├── entities.py               # Entity definities en Faker providers
│       └── templates.py              # Zin-templates per domein
└── output/
    └── eval_run_/
        ├── plots/
        │   ├── confusion_matrix.html/.png
        │   ├── metrics.html
        │   └── error_distribution.html
        ├── report.html
        └── eval_report.txt           # Overzicht error analysis
```

### CustomEvaluator

`evaluator.py` — Core evaluation logic:
- Laadt predictions via `src/api/services/text_analyzer.analyze(text, language="nl")`
- Matcht elk prediction tegen ground truth m.b.v. IoU
- Telt TP/FP/FN per entity type
- Bouwt confusion matrix

**Parameters:**
- `iou_threshold` (default 0.5): Minimum overlap om als "correct match" te tellen
- `score_threshold` (default 0.4): Minimum Presidio confidence score

### EvaluationPlotter

`plotter.py` — Visualisatie:
- `plot_confusion_matrix_heatmap()` → PNG (matplotlib) + HTML (plotly)
- `plot_metrics_bars()` → Grouped bar chart (Precision/Recall/F1)
- `plot_error_distribution()` → FP/FN stacked bars per entity
- `generate_html_report()` → Single-page report