"""Benchmark evaluatie voor OpenAnonymiser PII-detectie.

Vergelijkt karakter-gebaseerde span-voorspellingen met grondwaarheid per entiteitstype.
Geen externe tokenisatiemodellen vereist; werkt direct met onze Presidio-analyzer.

Gebruik:
    uv run benchmarks/evaluate.py
    uv run benchmarks/evaluate.py --data benchmarks/data/dutch_pii_sentences.json
    uv run benchmarks/evaluate.py --fail-on-threshold

Exit codes:
    0  — alle drempels gehaald (of --fail-on-threshold niet meegegeven)
    1  — een of meer drempels niet gehaald
    2  — fout in data of configuratie
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import click
import yaml

# Voeg project root toe zodat src/api importeerbaar is
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class _Span(NamedTuple):
    entity_type: str
    start: int
    end: int


@dataclass
class _Sample:
    text: str
    spans: list[_Span] = field(default_factory=list)


@dataclass
class _EntityMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _load_dataset(data_path: Path) -> list[_Sample]:
    """Laad gelabelde zinnen uit JSON naar _Sample objecten."""
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    samples: list[_Sample] = []
    for item in raw:
        spans = [
            _Span(
                entity_type=s["entity_type"],
                start=s["start_position"],
                end=s["end_position"],
            )
            for s in item.get("spans", [])
        ]
        samples.append(_Sample(text=item["full_text"], spans=spans))
    return samples


def _load_thresholds(thresholds_path: Path) -> dict[str, dict[str, float]]:
    """Laad minimale precision/recall drempels uit YAML."""
    return yaml.safe_load(thresholds_path.read_text(encoding="utf-8"))


def _iou(pred_start: int, pred_end: int, gt_start: int, gt_end: int) -> float:
    """Intersection over Union voor twee karakter-spans."""
    inter_start = max(pred_start, gt_start)
    inter_end = min(pred_end, gt_end)
    if inter_start >= inter_end:
        return 0.0
    intersection = inter_end - inter_start
    union = (pred_end - pred_start) + (gt_end - gt_start) - intersection
    return intersection / union if union else 0.0


def _evaluate(
    samples: list[_Sample],
    score_threshold: float,
    iou_threshold: float,
) -> dict[str, _EntityMetrics]:
    """Evalueer per entiteitstype op basis van karakter-span IoU."""
    from src.api.services.text_analyzer import analyze

    metrics: dict[str, _EntityMetrics] = defaultdict(lambda: _EntityMetrics())

    for sample in samples:
        results = analyze(sample.text, language="nl")
        predictions = [
            _Span(r.entity_type, r.start, r.end)
            for r in results
            if r.score >= score_threshold
        ]

        # Per ground-truth span: is er een overeenkomend predicted span?
        matched_preds: set[int] = set()
        for gt in sample.spans:
            found = False
            for i, pred in enumerate(predictions):
                if pred.entity_type == gt.entity_type and _iou(pred.start, pred.end, gt.start, gt.end) >= iou_threshold:
                    metrics[gt.entity_type].tp += 1
                    matched_preds.add(i)
                    found = True
                    break
            if not found:
                metrics[gt.entity_type].fn += 1

        # Niet-gematchte predictions zijn false positives
        for i, pred in enumerate(predictions):
            if i not in matched_preds:
                metrics[pred.entity_type].fp += 1

    return metrics


def _print_table(
    metrics: dict[str, _EntityMetrics],
    thresholds: dict[str, dict[str, float]],
) -> bool:
    """Print tabel met resultaten; geeft True als alle drempels gehaald zijn."""
    col_w = 20
    print(f"{'Entity':<{col_w}} {'Precision':>10} {'Recall':>8} {'F1':>8}  {'TP':>4} {'FP':>4} {'FN':>4}  Status")
    print("-" * 80)

    all_pass = True
    all_entities = sorted(set(metrics) | set(thresholds))

    for entity in all_entities:
        m = metrics.get(entity, _EntityMetrics())
        p, r, f1 = m.precision, m.recall, m.f1
        thresh = thresholds.get(entity, {})
        p_min = thresh.get("precision", 0.0)
        r_min = thresh.get("recall", 0.0)
        passed = p >= p_min and r >= r_min
        if not passed:
            all_pass = False
        status = "OK" if passed else f"FAIL (min p={p_min:.2f} r={r_min:.2f})"
        print(f"{entity:<{col_w}} {p:>10.2f} {r:>8.2f} {f1:>8.2f}  {m.tp:>4} {m.fp:>4} {m.fn:>4}  {status}")

    return all_pass


@click.command()
@click.option(
    "--data",
    "data_path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("benchmarks/data/dutch_pii_sentences.json"),
    show_default=True,
    help="Pad naar gelabelde testdata (JSON).",
)
@click.option(
    "--thresholds",
    "thresholds_path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("benchmarks/thresholds.yaml"),
    show_default=True,
    help="Pad naar drempelwaarden (YAML).",
)
@click.option(
    "--fail-on-threshold",
    is_flag=True,
    default=False,
    help="Exit 1 als een drempel niet gehaald wordt (voor CI).",
)
@click.option(
    "--score-threshold",
    type=float,
    default=0.4,
    show_default=True,
    help="Minimum Presidio confidence om een entiteit mee te tellen.",
)
@click.option(
    "--iou-threshold",
    type=float,
    default=0.5,
    show_default=True,
    help="Minimum overlap (IoU) tussen voorspelling en grondwaarheid.",
)
def main(
    data_path: Path,
    thresholds_path: Path,
    fail_on_threshold: bool,
    score_threshold: float,
    iou_threshold: float,
) -> None:
    """Evalueer PII-detectie precision/recall per entiteitstype."""
    print(f"Dataset:      {data_path}")
    print(f"Drempels:     {thresholds_path}")
    print(f"Score min:    {score_threshold}  |  IoU min: {iou_threshold}")
    print()

    try:
        dataset = _load_dataset(data_path)
        thresholds = _load_thresholds(thresholds_path)
    except (json.JSONDecodeError, yaml.YAMLError, KeyError) as exc:
        click.echo(f"Fout bij laden data/drempels: {exc}", err=True)
        sys.exit(2)

    print(f"Zinnen: {len(dataset)}\n")

    metrics = _evaluate(dataset, score_threshold, iou_threshold)
    all_pass = _print_table(metrics, thresholds)

    print()
    if not all_pass:
        print("Een of meer drempels niet gehaald.")
        if fail_on_threshold:
            sys.exit(1)
    else:
        print("Alle drempels gehaald.")


if __name__ == "__main__":
    main()
