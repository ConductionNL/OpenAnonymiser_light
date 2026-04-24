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

import hashlib
import io
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
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
    PiiCoverageMetrics,
    _EntityMetrics,
    _Sample,
    _Span,
    token_error_analysis,
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
        print("\n\U0001f4ca Partial Matches (misclassificaties: zelfde span, verkeerd type):")
        print("-" * 80)
        
        for err in errors["partial_matches"][:5]:
            pred_type = err.get("predicted_type", "?")
            print(f"\n  GT={err['entity_type']} → pred={pred_type}:")
            print(f"    Predicted:    '{err['predicted']}'")
            print(f"    Ground-truth: '{err['ground_truth']}'")
            print(f"    IoU: {err['iou']:.2f}")


def _load_label_map(label_map_path: Path) -> dict[str, str | None]:
    """Laad entity label mapping uit YAML.
    
    Labels met waarde null worden weggelaten uit evaluatie (model kan ze niet detecteren).
    """
    raw = yaml.safe_load(label_map_path.read_text(encoding="utf-8"))
    return {k: (v if v != "null" else None) for k, v in raw.items()}


def _print_pii_coverage(coverage: PiiCoverageMetrics) -> None:
    """Print binary PII coverage metrics."""
    print()
    print("PII Coverage (binary):")
    print("-" * 80)
    print(f"  Totaal samples:                {coverage.total_samples}")
    print(f"  Samples met PII (GT):          {coverage.samples_with_pii}")
    print(f"  Samples zonder PII (GT):       {coverage.samples_without_pii}")
    if coverage.samples_with_pii:
        print(
            f"  PII detected (≥1 pred):        {coverage.samples_pii_any_pred} "
            f"/ {coverage.samples_with_pii}  "
            f"({coverage.pii_recall_binary:.1%} binary recall)"
        )
        print(
            f"  PII volledig gemist (0 pred):  {coverage.samples_missed_entirely}"
        )


def _print_token_analysis(errors: dict, n: int = 10) -> None:
    """Print top-N token analysis over FP/FN errors."""
    analysis = token_error_analysis(errors, n=n)

    if analysis["fp_tokens"]:
        print("\n  Top FP tokens (onterecht als PII herkend):")
        for token, count in analysis["fp_tokens"]:
            print(f"    {token:<30} {count:>4}×")

    if analysis["fn_context_tokens"]:
        print("\n  Top FN context tokens (context rondom gemiste PII — potentiële context-woorden):")
        for token, count in analysis["fn_context_tokens"]:
            print(f"    {token:<30} {count:>4}×")

    if analysis["fp_by_entity"]:
        print("\n  FP tokens per entity type:")
        for entity, tokens in sorted(analysis["fp_by_entity"].items()):
            if tokens:
                top = ", ".join(f"'{t}'({c})" for t, c in tokens[:5])
                print(f"    {entity}: {top}")

    if analysis["fn_by_entity"]:
        print("\n  FN context tokens per entity type:")
        for entity, tokens in sorted(analysis["fn_by_entity"].items()):
            if tokens:
                top = ", ".join(f"'{t}'({c})" for t, c in tokens[:5])
                print(f"    {entity}: {top}")


def _save_run_metadata(
    output_dir: Path,
    data_path: Path,
    thresholds_path: Path,
    label_map_path: Path | None,
    score_threshold: float,
    iou_threshold: float,
    entity_filter: frozenset[str] | None,
    dataset_size: int,
    all_pass: bool,
    result: EvaluationResult,
) -> Path:
    """Sla run-configuratie en samenvatting op als run_metadata.json."""
    output_dir.mkdir(parents=True, exist_ok=True)

    def _sha256(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_ROOT,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()
    except Exception:
        git_sha = "unknown"

    pipeline_info: dict = {}
    try:
        from src.api.services.text_analyzer import get_analyzer
        engine = get_analyzer()
        pipeline_info["recognizers"] = [
            rec.name
            for rec in engine.registry.get_recognizers("nl", all_fields=True)
        ]
        pipeline_info["context_aware_enhancer"] = (
            engine.context_aware_enhancer.__class__.__name__
            if engine.context_aware_enhancer
            else "disabled"
        )
    except Exception as exc:
        pipeline_info["error"] = str(exc)

    plugins_path = _ROOT / "src" / "api" / "plugins.yaml"
    pipeline_info["plugins_yaml_sha256"] = (
        _sha256(plugins_path) if plugins_path.exists() else "unknown"
    )

    cov = result.pii_coverage
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "data": {
            "path": str(data_path),
            "sha256": _sha256(data_path),
            "num_samples": dataset_size,
        },
        "thresholds": {
            "path": str(thresholds_path),
        },
        "evaluation": {
            "score_threshold": score_threshold,
            "iou_threshold": iou_threshold,
            "label_map": str(label_map_path) if label_map_path else None,
            "entity_filter": sorted(entity_filter) if entity_filter else None,
            "all_thresholds_passed": all_pass,
        },
        "pipeline": pipeline_info,
        "summary": {
            "global_precision": round(float(result.global_precision), 4),
            "global_recall": round(float(result.global_recall), 4),
            "global_f1": round(float(result.global_f1), 4),
            "pii_recall_binary": round(float(cov.pii_recall_binary), 4),
            "samples_missed_entirely": cov.samples_missed_entirely,
        },
    }

    out_path = output_dir / "run_metadata.json"
    out_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return out_path


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
            "PHONE_NUMBER", "IBAN", "BSN", "DATE", "EMAIL", "ID_NO",
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
    "--label-map",
    "label_map_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Pad naar label-mapping YAML (bijv. benchmarks/label_maps/spacy_patterns.yaml).",
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
    label_map_path: Path | None,
) -> None:
    """Evalueer PII-detectie precision/recall per entiteitstype."""
    # Tee stdout to a buffer so we can save the full report to file
    _orig_stdout = sys.stdout
    _buf = io.StringIO()

    class _TeeWriter:
        def __init__(self, *writers):
            self.writers = writers
        def write(self, s):
            for w in self.writers:
                w.write(s)
        def flush(self):
            for w in self.writers:
                w.flush()

    sys.stdout = _TeeWriter(_orig_stdout, _buf)

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

    # Load optional label map
    label_map: dict[str, str | None] | None = None
    if label_map_path:
        try:
            label_map = _load_label_map(label_map_path)
            print(f"Label map:    {label_map_path}")
        except (yaml.YAMLError, KeyError) as exc:
            click.echo(f"Fout bij laden label map: {exc}", err=True)
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
    result = evaluator.evaluate(dataset, entities=entity_filter, label_map=label_map)
    
    # Filter thresholds to match evaluated entities
    filtered_thresholds = {
        k: v for k, v in thresholds.items()
        if entity_filter is None or k in entity_filter
    }
    
    all_pass = _print_table(result.metrics, filtered_thresholds)
    _print_pii_coverage(result.pii_coverage)

    if show_errors:
        _print_errors(result.errors)
        _print_token_analysis(result.errors)

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

        print("  \u2022 Saving run metadata...")
        meta_path = _save_run_metadata(
            output_dir=output_dir,
            data_path=data_path,
            thresholds_path=thresholds_path,
            label_map_path=label_map_path,
            score_threshold=score_threshold,
            iou_threshold=iou_threshold,
            entity_filter=entity_filter,
            dataset_size=len(dataset),
            all_pass=all_pass,
            result=result,
        )
        print(f"    \u2713 Saved: {meta_path}")

        print()

    print()
    if not all_pass:
        print("Een of meer drempels niet gehaald.")
    else:
        print("Alle drempels gehaald.")

    # Save full console output to eval_report.txt
    sys.stdout = _orig_stdout
    output_dir.mkdir(parents=True, exist_ok=True)
    report_txt = output_dir / "eval_report.txt"
    report_txt.write_text(_buf.getvalue(), encoding="utf-8")
    print(f"\n  ✓ Report saved: {report_txt}")

    if not all_pass and fail_on_threshold:
        sys.exit(1)


if __name__ == "__main__":
    main()
