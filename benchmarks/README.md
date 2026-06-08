# Benchmarks – PII-detectie evaluatie

**Voor spaCy vs GLiNER benchmark resultaten zie `spaCy_vs_GLiNER.md`.**

Evalueert PII-detectie met precision, recall en F1-score per entiteitstype.

## Testdata

Zie `generate_dataset.py` voor generatie details.

| Dataset | Zinnen | Beschrijving | Spans/entiteiten |
|---------|--------|--------------|-----------|
| `dutch_generated_dataset.json` | 599 | Primair — gesynthetiseerd multi-entity | 2235 |
| `dutch_edge_cases_dataset.json` | 131 | Edge cases en false-positive traps | 222 |


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

### GLiNER baseline
```bash
uv run benchmarks/evaluate.py --profile gliner --label-map benchmarks/label_maps/gliner_patterns.yaml
```

### SpaCy + patterns
```bash
uv run benchmarks/evaluate.py --profile spacy --label-map benchmarks/label_maps/spacy_patterns.yaml
```

### Met confusion matrix
```bash
uv run benchmarks/evaluate.py --profile gliner --label-map benchmarks/label_maps/gliner_patterns.yaml --plot --html-report --output-dir benchmarks/output/gliner_run
```

## Evaluation profiles

| Profile | Strategie | Threshold | Score | Doel |
|---------|-----------|-----------|-------|------|
| `gliner` | coverage | 0.3 | 0.45 | GLiNER baseline |
| `spacy` | iou | 0.5 | 0.4 | SpaCy comparison |

## Opties

| Optie | Type | Standaard | Beschrijving |
|-------|------|-----------|--------------|
| `--data` | path | `benchmarks/data/dutch_generated_dataset.json` | Pad naar gelabelde testdata (JSON) |
| `--thresholds` | path | `benchmarks/thresholds.yaml` | Pad naar drempelwaarden (YAML) |
| `--profile` | choice | geen | Evaluation profile: `gliner`, `spacy` |
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


## Code structuur

```
benchmarks/
├── README.md                         # Dit bestand
├── spaCy_vs_GLiNER.md                # Benchmarkresultaten
├── thresholds.yaml                   # P/R drempels per entity
├── data/
│   ├── dutch_generated_dataset.json  # Primair dataset (599 zinnen, 2235 spans)
│   ├── dutch_edge_cases_dataset.json # Edge cases (131 zinnen, 222 spans)
│   ├── generate_dataset.py           # Dataset generator
│   ├── validate_dataset.py           # Dataset validatie
│   └── generators/                   # Dataset generatie
│       ├── entities.py               # PII-generators (BSN, IBAN, etc.)
│       ├── templates.py              # Zin templates
│       └── edge_cases.py             # Edge case templates
├── matching/
│   ├── __init__.py                   # Exports
│   └── strategies.py                 # MatchingConfig, MatchingStrategy, SpanMatcher
├── profiles/
│   ├── gliner.yaml                   # Coverage-based (0.3)
│   └── spacy.yaml                    # IoU-based (0.5)
├── label_maps/                       # Label mappings dataset→pipeline
└── output/                           # Evaluatieruns (plots, reports)
```

## Drempels controleren

`thresholds.yaml` bevat minimale precision/recall per entity type. Met `--fail-on-threshold` exit de script met code 1 als een drempel niet gehaald wordt — handig voor CI/CD.

```bash
uv run benchmarks/evaluate.py --profile gliner --fail-on-threshold
```
