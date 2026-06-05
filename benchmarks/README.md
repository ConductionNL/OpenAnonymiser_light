# Benchmarks – PII-detectie evaluatie

Evalueert PII-detectie met precision, recall en F1-score per entiteitstype.

## Snelstart

### GLiNER baseline (aanbevolen)
```bash
uv run benchmarks/evaluate.py --profile gliner --label-map benchmarks/label_maps/gliner_patterns.yaml
```

### SpaCy + patterns (legacy)
```bash
uv run benchmarks/evaluate.py --profile spacy --label-map benchmarks/label_maps/spacy_patterns.yaml
```

### Met visualisaties
```bash
uv run benchmarks/evaluate.py --profile gliner --label-map benchmarks/label_maps/gliner_patterns.yaml --plot --html-report --output-dir benchmarks/output/gliner_run
```

## Evaluation profiles

| Profile | Strategie | Threshold | Score | Doel |
|---------|-----------|-----------|-------|------|
| `gliner` | coverage | 0.3 | 0.45 | GLiNER baseline |
| `spacy` | iou | 0.5 | 0.4 | SpaCy comparison |
| `strict` | iou | 0.75 | 0.4 | Strict evaluation |

## Opties

| Optie | Type | Standaard | Beschrijving |
|-------|------|-----------|--------------|
| `--data` | path | `benchmarks/data/dutch_generated_dataset.json` | Pad naar gelabelde testdata (JSON) |
| `--thresholds` | path | `benchmarks/thresholds.yaml` | Pad naar drempelwaarden (YAML) |
| `--profile` | choice | geen | Evaluation profile: `gliner`, `spacy`, `strict` |
| `--matching-strategy` | choice | `iou` | Span matching: `iou`, `partial`, `coverage` |
| `--score-threshold` | float | `0.4` | Minimum Presidio confidence |
| `--iou-threshold` | float | `0.5` | Minimum IoU (voor iou strategie) |
| `--coverage-threshold` | float | `0.3` | Minimum GT coverage (voor coverage strategie) |
| `--fail-on-threshold` | flag | false | Exit 1 als drempel niet gehaald (voor CI) |
| `--show-errors` | flag | false | Print FP/FN/partial matches |
| `--plot` | flag | false | Genereer visualisatie plots |
| `--html-report` | flag | false | Genereer single-page HTML report |
| `--output-dir` | path | `benchmarks/output/eval_run` | Output directory |

## Matching strategieen

| Strategie | Beschrijving |
|-----------|-------------|
| `iou` | Intersection-over-Union ≥ threshold |
| `partial` | Elke overlap > 0 telt |
| `coverage` | GT coverage ratio ≥ threshold |

**Waarom coverage voor GLiNER?** GLiNER produceert vaak spans die de kern correct detecteren maar grenzen iets afwijken. Coverage=0.3 tolereert dit terwijl IoU=0.5 te strikt is.

## Testdata

| Dataset | Zinnen | Beschrijving |
|---------|--------|--------------|
| `dutch_generated_dataset.json` | 534 | Primair — gesynthetiseerd multi-entity |
| `dutch_edge_cases_dataset.json` | 135 | Edge cases en false-positive traps |

Dataset formaat:
```json
[
  {
    "full_text": "Mijn BSN is 987654329",
    "spans": [{
      "entity_type": "BSN",
      "entity_value": "987654329",
      "start_position": 14,
      "end_position": 23
    }]
  }
]
```

## Code structuur

```
benchmarks/
├── evaluate.py                       # CLI entry point
├── evaluator.py                      # CustomEvaluator: matching + metrics
├── plotter.py                        # EvaluationPlotter: plots
├── generate_dataset.py               # Dataset generator
├── validate_dataset.py               # Dataset validatie
├── thresholds.yaml                   # P/R drempels per entity
├── matching/
│   └── strategies.py                 # MatchingConfig, MatchingStrategy, SpanMatcher
├── profiles/
│   ├── gliner.yaml                   # Coverage-based (0.3)
│   ├── spacy.yaml                    # IoU-based (0.5)
│   └── strict.yaml                   # IoU-based (0.75)
├── label_maps/                       # Label mappings dataset→pipeline
├── data/                             # Testdatasets
└── output/                           # Evaluatieruns
```

## Drempels controleren

`thresholds.yaml` bevat minimale precision/recall per entity type. Met `--fail-on-threshold` exit de script met code 1 als een drempel niet gehaald wordt — handig voor CI/CD.

```bash
uv run benchmarks/evaluate.py --profile gliner --fail-on-threshold
```
