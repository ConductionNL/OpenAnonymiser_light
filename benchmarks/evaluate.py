"""Benchmark evaluatie voor OpenAnonymiser PII-detectie.

Vergelijkt karakter-gebaseerde span-voorspellingen met grondwaarheid per entiteitstype.
Ondersteunt meerdere span-matching strategieen (IoU, coverage, fuzzy, semi-strict)
voor eerlijke evaluatie van GLiNER en andere NER modellen.

Gebruik:
    uv run benchmarks/evaluate.py
    uv run benchmarks/evaluate.py --profile gliner
    uv run benchmarks/evaluate.py --matching-strategy coverage --coverage-threshold 0.3
    uv run benchmarks/evaluate.py --compare
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

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.evaluator import (
    CustomEvaluator,
    EvaluationResult,
    PiiCoverageMetrics,
    _EntityMetrics,
    _Sample,
    _Span,
    collect_predictions,
    run_multi_strategy_evaluation,
    token_error_analysis,
)
from benchmarks.matching import (
    MatchingConfig,
    MatchingStrategy,
)
from benchmarks.matching.statistics import (
    ConfidenceInterval,
    bootstrap_ci_entity_level,
    bootstrap_ci_sample_level,
)
from benchmarks.plotter import EvaluationPlotter


def _load_dataset(data_path: Path) -> list[_Sample]:
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
    return yaml.safe_load(thresholds_path.read_text(encoding="utf-8"))


def _load_thresholds_profile(
    thresholds_path: Path, profile: str | None
) -> dict[str, dict[str, float]]:
    raw = yaml.safe_load(thresholds_path.read_text(encoding="utf-8"))
    if profile and profile in raw and isinstance(raw[profile], dict):
        entries = {
            k: v for k, v in raw[profile].items()
            if isinstance(v, dict) and k != "_matching"
        }
        return entries
    if all(isinstance(v, dict) for v in raw.values() if not isinstance(v, list)):
        has_nested = any(
            isinstance(v, dict) and any(isinstance(vv, dict) for vv in v.values())
            for v in raw.values()
        )
        if not has_nested:
            return raw
    return raw


def _collect_errors(
    samples: list[_Sample],
    score_threshold: float,
    matching_config: MatchingConfig,
) -> dict[str, list[dict]]:
    evaluator = CustomEvaluator(matching_config=matching_config)
    result = evaluator.evaluate(samples)
    return result.errors


def _print_errors(errors: dict[str, list[dict]], max_per_type: int = 3) -> None:
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

    if errors["partial_matches"]:
        print("\U0001f4ca Partial Matches (misclassificaties: zelfde span, verkeerd type):")
        print("-" * 80)

        for err in errors["partial_matches"][:5]:
            pred_type = err.get("predicted_type", "?")
            match_type = err.get("match_type", "")
            gt_cov = err.get("gt_coverage", 0.0)
            print(f"\n  GT={err['entity_type']} → pred={pred_type}:")
            print(f"    Predicted:    '{err['predicted']}'")
            print(f"    Ground-truth: '{err['ground_truth']}'")
            print(f"    IoU: {err['iou']:.2f}  GT coverage: {gt_cov:.2f}  Match: {match_type}")


def _load_label_map(label_map_path: Path) -> dict[str, str | None]:
    raw = yaml.safe_load(label_map_path.read_text(encoding="utf-8"))
    return {k: (v if v != "null" else None) for k, v in raw.items()}


_LABEL_MAPS_DIR = Path(__file__).resolve().parent / "label_maps"

_PROFILE_LABEL_MAPS: dict[str, Path] = {
    "gliner": _LABEL_MAPS_DIR / "gliner_patterns.yaml",
    "spacy": _LABEL_MAPS_DIR / "spacy_patterns.yaml",
}


def _print_pii_coverage(coverage: PiiCoverageMetrics) -> None:
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


def _print_ci(ci: ConfidenceInterval, label: str) -> None:
    print(f"  {label:<12} {ci.point_estimate:.3f}  [{ci.ci_lower:.3f}, {ci.ci_upper:.3f}]  (width={ci.width:.3f})")


def _print_bootstrap_cis(result: EvaluationResult) -> None:
    print("\nBootstrap 95% Confidence Intervals (sample-level):")
    print("-" * 80)

    global_ci = bootstrap_ci_sample_level(result.per_sample_counts)
    _print_ci(global_ci["precision"], "Precision")
    _print_ci(global_ci["recall"], "Recall")
    _print_ci(global_ci["f1"], "F1")

    print("\n  Per-entity CIs:")
    for entity in sorted(result.metrics.keys()):
        if entity == "O":
            continue
        m = result.metrics[entity]
        ci = bootstrap_ci_entity_level(m.tp, m.fp, m.fn)
        print(f"    {entity:<20} P: {ci['precision']}  R: {ci['recall']}  F1: {ci['f1']}")


def _save_run_metadata(
    output_dir: Path,
    data_path: Path,
    thresholds_path: Path,
    label_map_path: Path | None,
    matching_config: MatchingConfig,
    entity_filter: frozenset[str] | None,
    dataset_size: int,
    all_pass: bool,
    result: EvaluationResult,
) -> Path:
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
            "matching_strategy": matching_config.strategy.value,
            "iou_threshold": matching_config.iou_threshold,
            "coverage_threshold": matching_config.coverage_threshold,
            "length_ratio_threshold": matching_config.length_ratio_threshold,
            "score_threshold": matching_config.score_threshold,
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
    matching_config: MatchingConfig,
) -> dict[str, _EntityMetrics]:
    evaluator = CustomEvaluator(matching_config=matching_config)
    result = evaluator.evaluate(samples)
    return result.metrics


def _print_table(
    metrics: dict[str, _EntityMetrics],
    thresholds: dict[str, dict[str, float]],
) -> bool:
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


def _print_comparison_table(
    multi_results: dict[str, EvaluationResult],
) -> None:
    print("\nMulti-Strategy Comparison:")
    print("=" * 100)

    all_entities = sorted(
        set(e for r in multi_results.values() for e in r.metrics.keys())
    )

    header = f"{'Entity':<20}"
    for strategy_name in multi_results:
        header += f" | {strategy_name:^24} "
    print(header)

    subheader = f"{'':<20}"
    for strategy_name in multi_results:
        subheader += f" | {'P':>7} {'R':>7} {'F1':>7} "
    print(subheader)
    print("-" * len(subheader))

    for entity in all_entities:
        row = f"{entity:<20}"
        for strategy_name, result in multi_results.items():
            m = result.metrics.get(entity, _EntityMetrics())
            row += f" | {m.precision:>7.2f} {m.recall:>7.2f} {m.f1:>7.2f} "
        print(row)

    row = f"{'GLOBAL':<20}"
    for strategy_name, result in multi_results.items():
        row += f" | {result.global_precision:>7.2f} {result.global_recall:>7.2f} {result.global_f1:>7.2f} "
    print("-" * len(subheader))
    print(row)


@click.command()
@click.option(
    "--data",
    "data_path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("benchmarks/data/dutch_generated_dataset.json"),
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
    default=None,
    show_default=True,
    help="Minimum IoU voor span match (alleen voor iou strategie).",
)
@click.option(
    "--matching-strategy",
    type=click.Choice([s.value for s in MatchingStrategy]),
    default=None,
    help="Span matching strategie: iou, coverage, containment, fuzzy_length, semi_strict, partial.",
)
@click.option(
    "--coverage-threshold",
    type=float,
    default=0.3,
    show_default=True,
    help="Minimum GT coverage ratio (voor coverage strategie).",
)
@click.option(
    "--length-ratio-threshold",
    type=float,
    default=0.5,
    show_default=True,
    help="Minimum length ratio (voor fuzzy_length strategie).",
)
@click.option(
    "--profile",
    type=click.Choice(["gliner", "spacy", "strict"]),
    default=None,
    help="Evaluation profile: selects matching strategy, thresholds, and label map. Overrides --matching-strategy.",
)
@click.option(
    "--compare",
    is_flag=True,
    default=False,
    help="Run multi-strategy comparison (IoU, coverage, semi-strict) on the same predictions.",
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
    "--show-ci",
    is_flag=True,
    default=False,
    help="Print bootstrap 95% confidence intervals for P/R/F1.",
)
def main(
    data_path: Path,
    thresholds_path: Path,
    fail_on_threshold: bool,
    score_threshold: float,
    iou_threshold: float | None,
    matching_strategy: str | None,
    coverage_threshold: float,
    length_ratio_threshold: float,
    profile: str | None,
    compare: bool,
    show_errors: bool,
    plot: bool,
    html_report: bool,
    output_dir: Path,
    show_ci: bool,
) -> None:
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

    # Build MatchingConfig from profile or individual options
    if profile:
        matching_config = MatchingConfig.from_profile(profile)
        matching_config.score_threshold = score_threshold
    elif matching_strategy:
        strategy = MatchingStrategy(matching_strategy)
        matching_config = MatchingConfig(
            strategy=strategy,
            iou_threshold=iou_threshold or 0.5,
            coverage_threshold=coverage_threshold,
            length_ratio_threshold=length_ratio_threshold,
            score_threshold=score_threshold,
        )
    else:
        matching_config = MatchingConfig(
            iou_threshold=iou_threshold or 0.5,
            score_threshold=score_threshold,
        )

    print(f"Dataset:      {data_path}")
    print(f"Drempels:     {thresholds_path}")
    print(f"Strategy:     {matching_config.strategy.value}")
    print(f"Score min:    {matching_config.score_threshold}")
    if matching_config.strategy in (MatchingStrategy.IOU, MatchingStrategy.FUZZY_LENGTH):
        print(f"IoU min:      {matching_config.iou_threshold}")
    if matching_config.strategy == MatchingStrategy.COVERAGE:
        print(f"Coverage min: {matching_config.coverage_threshold}")
    if matching_config.strategy == MatchingStrategy.FUZZY_LENGTH:
        print(f"Length ratio: {matching_config.length_ratio_threshold}")
    print()

    try:
        dataset = _load_dataset(data_path)
        thresholds = _load_thresholds_profile(thresholds_path, profile)
    except (json.JSONDecodeError, yaml.YAMLError, KeyError) as exc:
        click.echo(f"Fout bij laden data/drempels: {exc}", err=True)
        sys.exit(2)

    label_map: dict[str, str | None] | None = None
    if profile and profile in _PROFILE_LABEL_MAPS:
        label_map_path = _PROFILE_LABEL_MAPS[profile]
        if label_map_path.exists():
            try:
                label_map = _load_label_map(label_map_path)
                print(f"Label map:    {label_map_path}")
            except (yaml.YAMLError, KeyError) as exc:
                click.echo(f"Fout bij laden label map: {exc}", err=True)
                sys.exit(2)

    print(f"Zinnen: {len(dataset)}\n")

    # --- Multi-strategy comparison mode ---
    if compare:
        configs = [
            MatchingConfig(strategy=MatchingStrategy.IOU, iou_threshold=0.5, score_threshold=score_threshold),
            MatchingConfig(strategy=MatchingStrategy.COVERAGE, coverage_threshold=0.3, score_threshold=score_threshold),
            MatchingConfig(strategy=MatchingStrategy.SEMI_STRICT, score_threshold=score_threshold),
        ]
        multi_results = run_multi_strategy_evaluation(
            dataset, configs, label_map=label_map,
            score_threshold=0.0,
        )
        _print_comparison_table(multi_results)

        if show_ci:
            for strategy_name, result in multi_results.items():
                print(f"\n--- {strategy_name} Confidence Intervals ---")
                _print_bootstrap_cis(result)

        sys.stdout = _orig_stdout
        output_dir.mkdir(parents=True, exist_ok=True)
        report_txt = output_dir / "eval_report.txt"
        report_txt.write_text(_buf.getvalue(), encoding="utf-8")
        print(f"\n  ✓ Report saved: {report_txt}")
        return

    # --- Single-strategy evaluation ---
    evaluator = CustomEvaluator(matching_config=matching_config)
    result = evaluator.evaluate(dataset, label_map=label_map)

    filtered_thresholds = thresholds

    all_pass = _print_table(result.metrics, filtered_thresholds)
    _print_pii_coverage(result.pii_coverage)

    if show_ci:
        _print_bootstrap_cis(result)

    if show_errors:
        _print_errors(result.errors)
        _print_token_analysis(result.errors)

    if plot:
        print(f"\n📊 Generating plots to: {output_dir}")
        plotter = EvaluationPlotter(result, output_dir)

        print("  • Generating confusion matrix (PNG)...")
        png_cm, _ = plotter.plot_confusion_matrix_heatmap()
        print(f"    ✓ Saved: {png_cm}")

        print("  • Generating metrics bar chart...")
        metrics_html = plotter.plot_metrics_bars()
        print(f"    ✓ Saved: {metrics_html}")

        print("  • Generating error distribution...")
        errors_html = plotter.plot_error_distribution()
        print(f"    ✓ Saved: {errors_html}")

        if html_report:
            print("  • Generating single-page HTML report...")
            report_path = plotter.generate_html_report()
            print(f"    ✓ Saved: {report_path}")

        print("  • Saving run metadata...")
        meta_path = _save_run_metadata(
            output_dir=output_dir,
            data_path=data_path,
            thresholds_path=thresholds_path,
            label_map_path=_PROFILE_LABEL_MAPS.get(profile) if profile else None,
            matching_config=matching_config,
            entity_filter=None,
            dataset_size=len(dataset),
            all_pass=all_pass,
            result=result,
        )
        print(f"    ✓ Saved: {meta_path}")

        print()

    print()
    if not all_pass:
        print("Een of meer drempels niet gehaald.")
    else:
        print("Alle drempels gehaald.")

    sys.stdout = _orig_stdout
    output_dir.mkdir(parents=True, exist_ok=True)
    report_txt = output_dir / "eval_report.txt"
    report_txt.write_text(_buf.getvalue(), encoding="utf-8")
    print(f"\n  ✓ Report saved: {report_txt}")

    if not all_pass and fail_on_threshold:
        sys.exit(1)


if __name__ == "__main__":
    main()
