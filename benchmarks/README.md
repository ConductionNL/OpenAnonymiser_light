# Benchmarks – PII-detectie evaluatie

Benchmark- en evaluatieuitrusting voor Dutch PII-detectie in OpenAnonymiser. Meet precision, recall en F1-score per entiteitstype met karakter-span IoU matching.

## Overzicht

De benchmark pipeline evalueert PII (Personally Identifiable Information) detectie door:

1. **Gelabelde testdata** inladen (JSON met ground-truth entity spans)
2. **PII-detectie** uitvoeren via de Presidio analyzer (pattern recognizers + optioneel NER/SpaCy/GLiNER)
3. **Span matching** met Intersection-over-Union (IoU) — minimaal 50% overlap standaard
4. **Metriek berekening** per entiteitstype: True Positives, False Positives, False Negatives → Precision/Recall/F1
5. **Visualisaties genereren**: confusion matrix, per-entity metrics, error breakdown
6. **Drempels controleren**: optionele CI/CD validatie met minimale P/R vereisten

### Waarom IoU-matching?

Character-level IoU matching is betrouwbaarder dan token-based matching voor irregular Nederlandse tekst. Voorbeeld:
- Ground truth: `"Jantje Jansen"` (chars 0-13)
- Prediction: `"Jansen"` (chars 8-13)
- IoU = 5 overlapping chars / 13 total chars union = 0.38 (misses met standaard 0.5 threshold)

## Snelstart

Configureer in `src/api/plugins.yaml` welke NLP recognizers/custom pattern recognizers ingezet worden tijdens de benchmark. Voorbeeld waar alleen gebenchmarked wordt met gliner:

```yaml
# src/api/plugins.yaml
recognizers:
  spacy:
    enabled: true  # ← Moet altijd true zijn, nodig voor de NLP engine init, als gliner enabled is wordt de spacy recognizer verwijderd zodat er alleen NER vanuit gliner komt
  gliner:
    enabled: true
  pattern:
    enabled: false
```

⚠️ **Belangrijk:** Standaard draait de API met SpaCy model (`nl_core_news_lg`) ingeschakeld. Voor **zuiver pattern-testen**, uncomment de twee regels in `src/api/services/text_analyzer.py` waar er wordt gechecked of de recognizer registry `has_gliner`.

### Basis:
```bash
uv run benchmarks/evaluate.py
```

Standaard draait de API met SpaCy model (`nl_core_news_lg`) ingeschakeld. Voor **zuiver pattern-testen**, zet SpaCy uit in `plugins.yaml` of gebruik `--pattern-only` om automatisch alleen pattern-based results te tellen.

Output: Per-entiteit Precision/Recall/F1 tabel met TP/FP/FN counts.

### Met visualisaties en error analyse
```bash
uv run benchmarks/evaluate.py \
  --pattern-only \
  --plot \
  --html-report \
  --show-errors
```

Genereert in `benchmarks/output/eval_run/`:
- `plots/confusion_matrix.html` — Interactive heatmap (ground truth vs predicted)
- `plots/metrics.html` — Bar chart met P/R/F1 per entity type
- `plots/error_distribution.html` — False Positives/Negatives breakdown
- `report.html` — Single-page HTML report met alle metrics

## Alle opties

| Optie | Type | Standaard | Beschrijving |
|-------|------|-----------|--------------|
| `--data` | path | `benchmarks/data/dutch_synth_multi_entity_dataset.json` | Pad naar gelabelde testdata (JSON) |
| `--thresholds` | path | `benchmarks/thresholds.yaml` | Pad naar drempelwaarden (YAML) |
| `--score-threshold` | float | `0.4` | Minimum Presidio confidence score (0.0-1.0) |
| `--iou-threshold` | float | `0.5` | Minimum IoU voor span match als "correct" (0.0-1.0) |
| `--fail-on-threshold` | flag | false | Exit code 1 als drempel niet gehaald (voor CI) |
| `--show-errors` | flag | false | Print false positives, false negatives, partial matches |
| `--plot` | flag | false | Genereer visualisatie plots (confusion matrix, metrics, errors) |
| `--plot-format` | choice | `html` | Plot format: `html` (interactief), `png` (statisch), `both` |
| `--html-report` | flag | false | Genereer single-page HTML report met alle data en plots |
| `--output-dir` | path | `benchmarks/output/eval_run` | Directory waar plots en reports opgeslagen worden |
| `--pattern-only` | flag | false | Test alleen pattern recognizers (geen NER/SpaCy/GLiNER) |
| `--entities` | string | None | Kommagescheiden entity types: `"PERSON,EMAIL,BSN"` (uppercase) |

## Gebruik voorbeelden

### 1. Snelle check (pattern recognizers)
```bash
uv run benchmarks/evaluate.py --pattern-only
```

Output:
```
Entity                Precision      Recall       F1     TP   FP   FN  Status
BSN                        1.00       1.00     1.00      6    0    0  OK
EMAIL                      1.00       1.00     1.00      9    0    0  OK
PHONE_NUMBER               0.78       1.00     0.88      7    2    0  OK
KVK_NUMBER                 0.70       1.00     0.82      7    3    0  OK
```

### 2. Full benchmark met visualisaties en report
```bash
uv run benchmarks/evaluate.py \
  --pattern-only \
  --plot both \
  --html-report \
  --output-dir benchmarks/output/eval_december_2024
```

Genereert PNG + HTML plots en single-page report.

### 3. Threshold validation (CI/CD mode)
```bash
uv run benchmarks/evaluate.py \
  --fail-on-threshold \
  --score-threshold 0.35 \
  --iou-threshold 0.4
```

Exit codes:
- **0** = alle drempels gehaald
- **1** = een of meer drempels niet gehaald (als `--fail-on-threshold`)
- **2** = config/data fout

### 4. Specifieke entiteiten debuggen
```bash
uv run benchmarks/evaluate.py \
  --entities "PHONE_NUMBER,KVK_NUMBER" \
  --show-errors \
  --plot
```

### 5. Strengere matching (higher IoU requirement)
```bash
uv run benchmarks/evaluate.py \
  --iou-threshold 0.75 \
  --show-errors
```

Minder false positives, maar meer false negatives op partial spans.

### 6. Custom dataset en output folder
```bash
uv run benchmarks/evaluate.py \
  --data benchmarks/data/dutch_pii_sentences.json \
  --output-dir benchmarks/output/eval_custom_v1 \
  --plot --html-report --show-errors
```

## Testdata beheren

### Gelabelde datasets

Beschikbare datasets in `benchmarks/data/`:
- **`dutch_pii_sentences.json`** — Gesynthetiseerd (klein), geen multi-entity zinnen
- **`dutch_synth_multi_entity_dataset.json`** — Gesynthetiseerd multi-entity (48 zinnen, 246 spans)

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
- Zorg dat alle gemarkeerde entiteiten in de tabel staan
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

## Configuratie via plugins.yaml

De benchmark-evaluator leest **altijd** `src/api/plugins.yaml` om te bepalen welke recognizers actief zijn. Dit beïnvloedt welke entity types beschikbaar zijn en hoe `--pattern-only` werkt.

### plugins.yaml structuur

```yaml
# src/api/plugins.yaml
recognizers:
  spacy:
    enabled: false        # SpaCy NER (PERSON, LOCATION, ORGANIZATION, etc.)
    model: "nl_core_news_lg"
    
  gliner:
    enabled: false        # GLiNER (advanced NER, optioneel)
    
  pattern:
    enabled: true         # Pattern recognizers (alle custompatterns)
    recognizers:
      - "DutchBSNRecognizer"
      - "DutchEmailRecognizer"
      - "DutchPhoneRecognizer"
      # etc.
```

### Effect op evaluatie

| Configuratie | `--pattern-only` resultaat | Volledige run resultaat |
|---|---|---|
| `spacy: false, pattern: true` | Alleen patterns | Nur patterns |
| `spacy: true, pattern: true` | Alleen patterns (gefilterd) | Patterns + NER types |
| `spacy: false, pattern: false` | Geen resultaten (FN overal) | Geen resultaten |

### Gebruiksscenario's

**Scenario 1: Pattern-only benchmark**
```yaml
recognizers:
  spacy:
    enabled: false
  pattern:
    enabled: true
```
```bash
uv run benchmarks/evaluate.py --pattern-only
# → Meet BSN, EMAIL, PHONE, etc. (patterns alleen)
```

**Scenario 2: Full benchmark (patterns + NER)**
```yaml
recognizers:
  spacy:
    enabled: true
  pattern:
    enabled: true
```
```bash
uv run benchmarks/evaluate.py --show-errors
# → Meet PERSON, LOCATION, EMAIL, BSN, PHONE, etc. (alles)
```

**Scenario 3: Alleen specifieke patterns**
```yaml
recognizers:
  spacy:
    enabled: false
  pattern:
    enabled: true
    recognizers:
      - "DutchBSNRecognizer"
      - "DutchEmailRecognizer"
      - "DutchPhoneRecognizer"
```
```bash
uv run benchmarks/evaluate.py --pattern-only
# → Meet alleen BSN, EMAIL, PHONE (subset)

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
- **F1** = Harmonisch gemiddelde P en R

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
├── thresholds.yaml                   # Optionele P/R drempels per entity
├── data/
│   ├── dutch_pii_sentences.json                    # Dataset v1
│   └── dutch_synth_multi_entity_dataset.json       # Dataset v2 (multi-entity)
└── output/
    └── eval_run_/ 
        ├── plots/
        │   ├── confusion_matrix.html/.png
        │   ├── metrics.html
        │   └── error_distribution.html
        └── report.html
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

## Troubleshooting

| Probleem | Oorzaak | Oplossing |
|----------|---------|-----------|
| `ModuleNotFoundError: No module named 'src.api'` | Python path niet ingesteld | Voer `uv run` uit vanuit project root |
| `No predictions / alle FN` | Model/API werkt niet of plugins.yaml issue | Check of API draait (`uv run api.py`), plugin config in `src/api/plugins.yaml` correct (spacy/pattern `enabled` check) |
| `--pattern-only geeft NER results` | SpaCy nog ingeschakeld in plugins.yaml | Zet `spacy: enabled: false` in `src/api/plugins.yaml` |
| `Lage scores op patterns` | Pattern regex bug | Controleer `src/api/utils/patterns.py` |
| `Visualisaties niet gegenereerd` | `--plot` flag vergeten | Voeg `--plot --html-report` toe |
| `YAML parse error in thresholds.yaml` | Indentatie fout | Gebruik spaces (geen tabs); valideer met `yamllint` |
| `FileNotFoundError: data path` | Dataset pad verkeerd | Check `--data` argument of bestand bestaat |

## Zie ook

- [docs/02-api-reference.md](../docs/02-api-reference.md) — API endpoints
- [src/api/utils/patterns.py](../src/api/utils/patterns.py) — Pattern recognizer definities
- [CLAUDE.md](../CLAUDE.md) — Project conventions
