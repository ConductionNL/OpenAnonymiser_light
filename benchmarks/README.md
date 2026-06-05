# Benchmarks – PII-detectie evaluatie

Benchmark- en evaluatieuitrusting voor Dutch PII-detectie in OpenAnonymiser. Meet precision, recall en F1-score per entiteitstype met configureerbare span-matching strategieen.

## Overzicht

De benchmark pipeline evalueert PII (Personally Identifiable Information) detectie door:

1. **Gelabelde testdata** inladen (JSON met ground-truth entity spans)
2. **PII-detectie** uitvoeren via de Presidio analyzer (pattern recognizers + NER)
3. **Span matching** met configureerbare strategieen (IoU, coverage, fuzzy, semi-strict)
4. **Label mapping** toepassen om dataset-labels te mappen op pipeline-labels
5. **Metriek berekening** per entiteitstype: True Positives, False Positives, False Negatives → Precision/Recall/F1
6. **Bootstrap confidence intervallen** (95% CI via sample-level resampling)
7. **Visualisaties genereren**: confusion matrix, per-entity metrics, error breakdown, CI bars
8. **Drempels controleren**: optionele CI/CD validatie met minimale P/R vereisten

### Span-matching strategieen

De benchmark ondersteunt meerdere matching strategieen om eerlijk te evalueren met verschillende NER modellen:

| Strategie | Beschrijving | Geschikt voor |
|-----------|-------------|---------------|
| `iou` | Standard Intersection-over-Union (≥ threshold) | spaCy (token-aligned boundaries) |
| `coverage` | GT coverage ratio (hoeveel van GT zit in pred?) | GLiNER (boundary drift) |
| `containment` | Een span bevat de andere volledig | Asymmetrische boundary errors |
| `fuzzy_length` | IoU + length-ratio tolerantie | Verschillende span breedtes |
| `semi_strict` | Elke karakter-overlap telt (MUC-stijl) | Meest tolerante matching |
| `partial` | Elke IoU > 0 telt als match | Tussen IoU en semi-strict |

**Waarom coverage-based matching voor GLiNER?**

GLiNER produceert vaak spans die de kern van een entiteit correct detecteren, maar de grenzen iets afwijken:

- GT: `"Kalverstraat 58, 5506HH Capelle aan den IJssel"` → Pred: `"Capelle aan den IJssel"` → IoU=0.43, **GT coverage=0.43**
- GT: `"Jansen"` → Pred: `"de heer Jansen"` → IoU=0.50, **GT coverage=1.0**

Met IoU=0.5 zijn beide een miss. Met coverage=0.3 is het tweede een match, en het eerste instelbaar.

## Snelstart

### GLiNER baseline (aanbevolen)
```bash
uv run benchmarks/evaluate.py \
  --profile gliner \
  --label-map benchmarks/label_maps/gliner_patterns.yaml
```

### SpaCy + patterns (legacy)
```bash
uv run benchmarks/evaluate.py \
  --profile spacy \
  --label-map benchmarks/label_maps/spacy_patterns.yaml
```

### Multi-strategy vergelijking (A/B test)
```bash
uv run benchmarks/evaluate.py \
  --compare \
  --label-map benchmarks/label_maps/gliner_patterns.yaml
```

Draait IoU, coverage, en semi-strict op dezelfde voorspellingen en toont een vergelijkingstabel.

### Met visualisaties, CI en error analyse
```bash
uv run benchmarks/evaluate.py \
  --profile gliner \
  --label-map benchmarks/label_maps/gliner_patterns.yaml \
  --plot --html-report --show-errors --show-ci \
  --output-dir benchmarks/output/gliner_run
```

## Evaluation profiles

Profiles bundelen matching-strategie + drempelwaarden in een enkel commando:

| Profile | Strategie | IoU/Coverage | Score | Doel |
|---------|-----------|-------------|-------|------|
| `gliner` | coverage | 0.3 | 0.45 | GLiNER baseline |
| `spacy` | iou | 0.5 | 0.4 | SpaCy comparison |
| `strict` | iou | 0.75 | 0.4 | Upper-bound (near-exact) |

Custom profielen in `benchmarks/profiles/` aanmaken.

## Alle opties

| Optie | Type | Standaard | Beschrijving |
|-------|------|-----------|--------------|
| `--data` | path | `benchmarks/data/dutch_generated_dataset.json` | Pad naar gelabelde testdata (JSON) |
| `--thresholds` | path | `benchmarks/thresholds.yaml` | Pad naar drempelwaarden (YAML) |
| `--label-map` | path | geen | YAML label mapping (dataset→pipeline) |
| `--profile` | choice | geen | Evaluation profile: `gliner`, `spacy`, `strict` |
| `--matching-strategy` | choice | `iou` | Span matching strategie |
| `--score-threshold` | float | `0.4` | Minimum Presidio confidence score |
| `--iou-threshold` | float | `0.5` | Minimum IoU (voor iou/fuzzy strategie) |
| `--coverage-threshold` | float | `0.3` | Minimum GT coverage (voor coverage strategie) |
| `--length-ratio-threshold` | float | `0.5` | Minimum length ratio (voor fuzzy strategie) |
| `--compare` | flag | false | Multi-strategy vergelijking (IoU + coverage + semi-strict) |
| `--show-ci` | flag | false | Print bootstrap 95% confidence intervallen |
| `--fail-on-threshold` | flag | false | Exit code 1 als drempel niet gehaald (voor CI) |
| `--show-errors` | flag | false | Print FP/FN/partial matches |
| `--plot` | flag | false | Genereer visualisatie plots |
| `--plot-format` | choice | `html` | Plot format: `html`, `png`, `both` |
| `--html-report` | flag | false | Genereer single-page HTML report |
| `--output-dir` | path | `benchmarks/output/eval_run` | Output directory |
| `--entities` | string | None | Kommagescheiden entity types: `"PERSON,EMAIL,BSN"` |
| `--pattern-only` | flag | false | Test alleen custom pattern recognizers |

## Bootstrap Confidence Intervals

Met `--show-ci` worden 95% bootstrap confidence intervallen berekend via sample-level resampling (10.000 iteraties). Dit geeft eerlijke onzekerheidschattingen die within-sentence correlaties behouden.

Voorbeeld output:
```
Bootstrap 95% Confidence Intervals (sample-level):
  Precision    0.820  [0.790, 0.848]  (width=0.058)
  Recall       0.878  [0.854, 0.900]  (width=0.046)
  F1           0.848  [0.826, 0.869]  (width=0.043)
```

## Multi-strategy vergelijking

Met `--compare` wordt dezelfde dataset geëvalueerd onder drie strategieen zonder het model opnieuw te draaien:

```
Multi-Strategy Comparison:
Entity               |         iou          |      coverage        |   semi_strict
                     | P      R      F1     | P      R      F1     | P      R      F1
PERSON               | 0.83   0.90   0.86   | 0.81   0.94   0.87   | 0.78   0.96   0.86
LOCATION             | 0.79   0.78   0.79   | 0.74   0.88   0.80   | 0.71   0.91   0.80
```

Dit toont transparant hoeveel van de score toe te schrijven is aan matching-tolerantie vs genuine detectie.

## Testdata

### Beschikbare datasets

| Dataset | Zinnen | Beschrijving |
|---------|--------|--------------|
| `dutch_generated_dataset.json` | 534 | Primair — gesynthetiseerd multi-entity (23 entity types) |
| `dutch_edge_cases_dataset.json` | 135 | Edge cases voor grensgevallen |

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
      }
    ]
  }
]
```

## Code structuur

```
benchmarks/
├── README.md                         # Dit bestand
├── evaluate.py                       # CLI entry point (click decorators)
├── evaluator.py                      # CustomEvaluator: span matching + metrics
├── plotter.py                        # EvaluationPlotter: plots + CI display
├── generate_dataset.py               # Dataset generator (Faker-based)
├── validate_dataset.py               # Dataset validatie (span-checks)
├── thresholds.yaml                   # P/R drempels per entity + per profile
├── matching/                         # Span matching module
│   ├── __init__.py                   # Exports
│   ├── strategies.py                 # MatchingStrategy, SpanMatcher, MatchingConfig
│   └── statistics.py                 # Bootstrap CI, ConfidenceInterval
├── profiles/                         # Evaluation profiles
│   ├── gliner.yaml                   # GLiNER baseline (coverage=0.3)
│   ├── spacy.yaml                    # SpaCy comparison (iou=0.5)
│   └── strict.yaml                   # Strict evaluation (iou=0.75)
├── label_maps/
│   ├── spacy_patterns.yaml           # Label map: SpaCy NER + patterns
│   └── gliner_patterns.yaml          # Label map: GLiNER + patterns
├── data/
│   ├── dutch_generated_dataset.json  # Primair dataset
│   ├── dutch_edge_cases_dataset.json # Edge cases
│   └── generators/                   # Dataset generatie logica
└── output/
    └── eval_run/
        ├── plots/
        │   ├── confusion_matrix.html/.png
        │   ├── metrics.html
        │   ├── error_distribution.html
        │   ├── multi_strategy_comparison.html
        │   └── ci_bars.html
        ├── report.html
        ├── run_metadata.json
        └── eval_report.txt
```

### CustomEvaluator

`evaluator.py` — Core evaluation logic:
- Configureerbare span matching via `MatchingConfig` (IoU, coverage, containment, fuzzy, semi-strict)
- Laadt predictions via `src/api/services/text_analyzer.analyze(text, language="nl")`
- Matcht elk prediction tegen ground truth m.b.v. de geselecteerde strategie
- Telt TP/FP/FN per entity type + per-sample counts voor bootstrap CI
- Bouwt confusion matrix
- `evaluate_from_cache()` hergebruikt predictions voor multi-strategy vergelijking
- `run_multi_strategy_evaluation()` draait meerdere strategieen op dezelfde predictions

### MatchingConfig

`matching/strategies.py` — Configuratie en matching:
- `MatchingStrategy` enum: iou, coverage, containment, fuzzy_length, semi_strict, partial
- `MatchingConfig`: strategie + thresholds (iou_threshold, coverage_threshold, etc.)
- `SpanMatcher`: berekent `SpanMatch` met score, iou, gt_coverage, pred_coverage, length_ratio
- `MatchingConfig.from_profile("gliner")`: laad vooraf gedefinieerde profielen

### Bootstrap CI

`matching/statistics.py` — Statistische validatie:
- `bootstrap_ci_sample_level()`: sample-level resampling (behoudt within-sentence correlaties)
- `bootstrap_ci_entity_level()`: entity-level resampling (sneller, minder conservatief)
- `ConfidenceInterval`: point_estimate, ci_lower, ci_upper, width
