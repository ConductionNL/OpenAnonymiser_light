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
from pathlib import Path

import click
import yaml

# Voeg project root toe zodat src/api importeerbaar is
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Import custom evaluation classes from evaluator module
from benchmarks.evaluator import (
    CustomEvaluator,
    EvaluationResult,
    _EntityMetrics,
    _Sample,
    _Span,
)
from benchmarks.plotter import EvaluationPlotter


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


def _collect_errors(
    samples: list[_Sample],
    score_threshold: float,
    iou_threshold: float,
) -> dict[str, list[dict]]:
    """Verzamel false positives, false negatives en partial matches.
    
    Wrapper around CustomEvaluator for backwards compatibility.
    
    Returns:
        {
            "false_positives": [...],
            "false_negatives": [...],
            "partial_matches": [...],
        }
    """
    evaluator = CustomEvaluator(
        iou_threshold=iou_threshold,
        score_threshold=score_threshold,
    )
    result = evaluator.evaluate(samples)
    return result.errors


def _print_errors(errors: dict[str, list[dict]], max_per_type: int = 3) -> None:
    """Print false positives, false negatives en partial matches."""
    
    # False Positives
    if errors["false_positives"]:
        print("\n❌ False Positives (modeldetecteerde iets wat niet klopt):")
        print("-" * 80)
        
        by_type = defaultdict(list)
        for err in errors["false_positives"]:
            by_type[err["entity_type"]].append(err)
        
        for entity_type in sorted(by_type.keys()):
            items = by_type[entity_type][:max_per_type]
            print(f"\n  {entity_type} ({len(by_type[entity_type])} total):")
            for err in items:
                print(f"    • '{err['text']}'")
                print(f"      Context: ...{err['context']}...")
    
    # False Negatives
    if errors["false_negatives"]:
        print("\n⚠️  False Negatives (model miste deze):")
        print("-" * 80)
        
        by_type = defaultdict(list)
        for err in errors["false_negatives"]:
            by_type[err["entity_type"]].append(err)
        
        for entity_type in sorted(by_type.keys()):
            items = by_type[entity_type][:max_per_type]
            print(f"\n  {entity_type} ({len(by_type[entity_type])} total):")
            for err in items:
                print(f"    • '{err['text']}'")
                print(f"      Context: ...{err['context']}...")
    
    # Partial Matches
    if errors["partial_matches"]:
        print("\n📊 Partial Matches (te laag IoU):")
        print("-" * 80)
        
        for err in errors["partial_matches"][:5]:
            print(f"\n  {err['entity_type']}:")
            print(f"    Predicted:   '{err['predicted']}'")
            print(f"    Ground-truth: '{err['ground_truth']}'")
            print(f"    IoU: {err['iou']:.2f}")


def _evaluate(
    samples: list[_Sample],
    score_threshold: float,
    iou_threshold: float,
) -> dict[str, _EntityMetrics]:
    """Evalueer per entiteitstype op basis van karakter-span IoU.
    
    Wrapper around CustomEvaluator for backwards compatibility.
    """
    evaluator = CustomEvaluator(
        iou_threshold=iou_threshold,
        score_threshold=score_threshold,
    )
    result = evaluator.evaluate(samples)
    return result.metrics


def _get_pattern_entities() -> frozenset[str]:
    """Laad pattern recognizer entity types uit plugins.yaml."""
    try:
        from src.api.utils.plugin_loader import load_plugins
        cfg = load_plugins()
        return cfg.pattern_entity_types
    except Exception:
        # Fallback als plugin loading mislukt
        return frozenset([
            "PHONE_NUMBER", "IBAN", "BSN", "DATE_TIME", "EMAIL", "ID_NO",
            "DRIVERS_LICENSE", "VAT_NUMBER", "KVK_NUMBER", "LICENSE_PLATE",
            "IP_ADDRESS", "CASE_NO"
        ])


def _filter_entities(
    metrics: dict[str, _EntityMetrics],
    thresholds: dict[str, dict[str, float]],
    entity_filter: frozenset[str] | None,
) -> tuple[dict[str, _EntityMetrics], dict[str, dict[str, float]]]:
    """Filter metrics en thresholds op bepaalde entity types."""
    if not entity_filter:
        return metrics, thresholds
    return (
        {k: v for k, v in metrics.items() if k in entity_filter},
        {k: v for k, v in thresholds.items() if k in entity_filter},
    )


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
    default=Path("benchmarks/data/dutch_synth_multi_entity_dataset.json"),
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
@click.option(
    "--show-errors",
    is_flag=True,
    default=False,
    help="Print false positives, false negatives, partial matches.",
)
@click.option(
    "--plot",
    is_flag=True,
    default=False,
    help="Generate visualization plots (confusion matrix, metrics, errors).",
)
@click.option(
    "--plot-format",
    type=click.Choice(["html", "png", "both"], case_sensitive=False),
    default="html",
    show_default=True,
    help="Plot format: html (interactive), png (static), or both.",
)
@click.option(
    "--html-report",
    is_flag=True,
    default=False,
    help="Generate single-page HTML report with all metrics and plots.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("benchmarks/output/eval_run"),
    show_default=True,
    help="Directory where plots and reports will be saved.",
)
@click.option(
    "--pattern-only",
    is_flag=True,
    default=False,
    help="Test alleen custom pattern recognizers (geen NER).",
)
@click.option(
    "--entities",
    type=str,
    default=None,
    help="Kommagescheiden lijst van entity types om te testen (bijv: PERSON,EMAIL,BSN).",
)
def main(
    data_path: Path,
    thresholds_path: Path,
    fail_on_threshold: bool,
    score_threshold: float,
    iou_threshold: float,
    show_errors: bool,
    plot: bool,
    plot_format: str,
    html_report: bool,
    output_dir: Path,
    pattern_only: bool,
    entities: str | None,
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

    # Use new CustomEvaluator directly instead of _evaluate()
    evaluator = CustomEvaluator(
        iou_threshold=iou_threshold,
        score_threshold=score_threshold,
    )
    
    # Determine entity filter
    entity_filter: frozenset[str] | None = None
    if pattern_only:
        entity_filter = _get_pattern_entities()
        print(f"Filter: Alleen pattern recognizers ({', '.join(sorted(entity_filter))})\n")
    elif entities:
        entity_filter = frozenset(e.strip().upper() for e in entities.split(","))
        print(f"Filter: {', '.join(sorted(entity_filter))}\n")
    
    # Run evaluation
    result = evaluator.evaluate(dataset, entities=entity_filter)
    
    # Filter thresholds to match evaluated entities
    filtered_thresholds = {
        k: v for k, v in thresholds.items()
        if entity_filter is None or k in entity_filter
    }
    
    all_pass = _print_table(result.metrics, filtered_thresholds)

    if show_errors:
        _print_errors(result.errors)

    # Generate plots if requested
    if plot:
        print(f"\n📊 Generating plots to: {output_dir}")
        plotter = EvaluationPlotter(result, output_dir)
        
        if plot_format.lower() in ["html", "both"]:
            print("  • Generating confusion matrix heatmap (HTML)...")
            _, html_cm = plotter.plot_confusion_matrix_heatmap()
            print(f"    ✓ Saved: {html_cm}")
            
            print("  • Generating metrics bar chart...")
            metrics_html = plotter.plot_metrics_bars()
            print(f"    ✓ Saved: {metrics_html}")
            
            print("  • Generating error distribution...")
            errors_html = plotter.plot_error_distribution()
            print(f"    ✓ Saved: {errors_html}")
        
        if plot_format.lower() in ["png", "both"]:
            print("  • Generating confusion matrix (PNG)...")
            png_cm, _ = plotter.plot_confusion_matrix_heatmap()
            print(f"    ✓ Saved: {png_cm}")
        
        if html_report:
            print("  • Generating single-page HTML report...")
            report_path = plotter.generate_html_report()
            print(f"    ✓ Saved: {report_path}")
        
        print()

    print()
    if not all_pass:
        print("Een of meer drempels niet gehaald.")
        if fail_on_threshold:
            sys.exit(1)
    else:
        print("Alle drempels gehaald.")


if __name__ == "__main__":
    main()
