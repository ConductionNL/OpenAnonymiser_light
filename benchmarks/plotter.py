"""PII Evaluation Result Visualization.

Generates plots from EvaluationResult objects:
  - Confusion matrix heatmap (matplotlib + plotly)
  - Per-entity metrics bar charts (plotly)
  - Error distribution plots (plotly)
  - Multi-strategy comparison table
  - Confidence interval display
  - Combined HTML report

Usage:
    from benchmarks.plotter import EvaluationPlotter
    from benchmarks.evaluator import CustomEvaluator

    evaluator = CustomEvaluator()
    result = evaluator.evaluate(dataset)

    plotter = EvaluationPlotter(result, output_dir=Path("./output"))
    plotter.plot_confusion_matrix_heatmap()
    plotter.plot_metrics_bars()
    plotter.plot_error_distribution()
    plotter.generate_html_report()
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import seaborn as sns
from benchmarks.evaluator import EvaluationResult, _EntityMetrics


class EvaluationPlotter:
    def __init__(self, result: EvaluationResult, output_dir: Path) -> None:
        self.result = result
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir = self.output_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)

    def plot_confusion_matrix_heatmap(self) -> tuple[Path, Path]:
        matrix = self.result.confusion_matrix
        entities = self.result.entity_types

        plt.figure(figsize=(10, 8))
        sns.heatmap(
            matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=entities,
            yticklabels=entities,
            cbar_kws={"label": "Count"},
        )
        strategy_label = ""
        if self.result.matching_config:
            strategy_label = f" ({self.result.matching_config.strategy.value})"
        plt.title(f"Confusion Matrix{strategy_label}: Predicted vs Ground Truth Entities")
        plt.xlabel("Predicted Entity Type")
        plt.ylabel("Ground Truth Entity Type")
        plt.tight_layout()

        png_path = self.plots_dir / "confusion_matrix.png"
        plt.savefig(png_path, dpi=150, bbox_inches="tight")
        plt.close()

        fig = go.Figure(
            data=go.Heatmap(
                z=matrix,
                x=entities,
                y=entities,
                colorscale="Blues",
                text=matrix,
                texttemplate="%{text}",
                textfont={"size": 10},
                colorbar={"title": "Count"},
            )
        )
        fig.update_layout(
            title=f"Confusion Matrix{strategy_label}: Predicted vs Ground Truth Entities",
            xaxis_title="Predicted Entity Type",
            yaxis_title="Ground Truth Entity Type",
            width=800,
            height=700,
        )

        html_path = self.plots_dir / "confusion_matrix.html"
        fig.write_html(str(html_path))

        return png_path, html_path

    def plot_metrics_bars(self) -> Path:
        metrics_data: dict[str, list[Any]] = {
            "Entity": [],
            "Precision": [],
            "Recall": [],
            "F1": [],
        }

        for entity in self.result.entity_types:
            if entity == "O":
                continue
            if entity not in self.result.metrics:
                continue
            m = self.result.metrics[entity]
            metrics_data["Entity"].append(entity)
            metrics_data["Precision"].append(m.precision)
            metrics_data["Recall"].append(m.recall)
            metrics_data["F1"].append(m.f1)

        fig = go.Figure(
            data=[
                go.Bar(x=metrics_data["Entity"], y=metrics_data["Precision"], name="Precision"),
                go.Bar(x=metrics_data["Entity"], y=metrics_data["Recall"], name="Recall"),
                go.Bar(x=metrics_data["Entity"], y=metrics_data["F1"], name="F1"),
            ]
        )

        strategy_label = ""
        if self.result.matching_config:
            strategy_label = f" ({self.result.matching_config.strategy.value})"

        fig.update_layout(
            title=f"Per-Entity Metrics{strategy_label}: Precision, Recall, F1",
            xaxis_title="Entity Type",
            yaxis_title="Score",
            barmode="group",
            height=600,
            width=1000,
            hovermode="x unified",
        )

        html_path = self.plots_dir / "metrics.html"
        fig.write_html(str(html_path))

        return html_path

    def plot_error_distribution(self) -> Path:
        error_data: dict[str, list[Any]] = {"Entity": [], "False Positives": [], "False Negatives": []}

        for entity in self.result.entity_types:
            if entity == "O":
                continue
            if entity not in self.result.metrics:
                continue
            m = self.result.metrics[entity]
            error_data["Entity"].append(entity)
            error_data["False Positives"].append(m.fp)
            error_data["False Negatives"].append(m.fn)

        fig = go.Figure(
            data=[
                go.Bar(x=error_data["Entity"], y=error_data["False Positives"], name="False Positives"),
                go.Bar(x=error_data["Entity"], y=error_data["False Negatives"], name="False Negatives"),
            ]
        )

        fig.update_layout(
            title="Error Distribution by Entity Type",
            xaxis_title="Entity Type",
            yaxis_title="Count",
            barmode="group",
            height=600,
            width=1000,
            hovermode="x unified",
        )

        html_path = self.plots_dir / "error_distribution.html"
        fig.write_html(str(html_path))

        return html_path

    def plot_multi_strategy_comparison(
        self, multi_results: dict[str, EvaluationResult]
    ) -> Path:
        all_entities = sorted(
            set(e for r in multi_results.values() for e in r.metrics.keys())
        )

        fig = go.Figure()
        strategies = list(multi_results.keys())

        for metric_name, color in [("F1", "#2196F3"), ("Precision", "#4CAF50"), ("Recall", "#FF9800")]:
            for i, strategy in enumerate(strategies):
                result = multi_results[strategy]
                values = []
                for entity in all_entities:
                    m = result.metrics.get(entity, _EntityMetrics())
                    values.append(getattr(m, metric_name.lower(), 0.0))

                fig.add_trace(go.Bar(
                    name=f"{strategy} - {metric_name}",
                    x=all_entities,
                    y=values,
                    marker_color=color,
                    opacity=0.5 + 0.5 * (i / max(len(strategies) - 1, 1)),
                ))

        fig.update_layout(
            title="Multi-Strategy Comparison: P/R/F1 by Entity Type",
            xaxis_title="Entity Type",
            yaxis_title="Score",
            barmode="group",
            height=700,
            width=1200,
            hovermode="x unified",
        )

        html_path = self.plots_dir / "multi_strategy_comparison.html"
        fig.write_html(str(html_path))

        return html_path

    def generate_html_report(self) -> Path:
        metrics_html = self._build_metrics_table()
        error_summary = self._build_error_summary()
        strategy_info = self._build_strategy_info()
        confusion_matrix_b64 = self._embed_plot_as_base64(self.plots_dir / "confusion_matrix.png")

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PII Evaluation Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        .metrics-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: #f9f9f9;
            border-left: 4px solid #007bff;
            padding: 15px;
            border-radius: 4px;
        }}
        .metric-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #007bff;
        }}
        .metric-card .label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #f0f0f0;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .plot-container {{
            margin: 30px 0;
            border: 1px solid #eee;
            border-radius: 4px;
            overflow: hidden;
        }}
        .strategy-info {{
            background: #e8f4fd;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>PII Detection Evaluation Report</h1>

        {strategy_info}

        <h2>Global Metrics</h2>
        <div class="metrics-summary">
            <div class="metric-card">
                <div class="value">{self.result.global_precision:.3f}</div>
                <div class="label">Precision</div>
            </div>
            <div class="metric-card">
                <div class="value">{self.result.global_recall:.3f}</div>
                <div class="label">Recall</div>
            </div>
            <div class="metric-card">
                <div class="value">{self.result.global_f1:.3f}</div>
                <div class="label">F1 Score</div>
            </div>
            <div class="metric-card">
                <div class="value">{self.result.global_tp}</div>
                <div class="label">True Positives</div>
            </div>
            <div class="metric-card">
                <div class="value">{self.result.global_fp}</div>
                <div class="label">False Positives</div>
            </div>
            <div class="metric-card">
                <div class="value">{self.result.global_fn}</div>
                <div class="label">False Negatives</div>
            </div>
        </div>

        <h2>Per-Entity Metrics</h2>
        {metrics_html}

        <h2>Error Summary</h2>
        {error_summary}

        <div class="footer">
            <p>Generated by OpenAnonymiser Evaluation Pipeline</p>
        </div>
    </div>
</body>
</html>
        """

        report_path = self.output_dir / "report.html"
        report_path.write_text(html_content, encoding="utf-8")

        return report_path

    def _build_strategy_info(self) -> str:
        cfg = self.result.matching_config
        if cfg is None:
            return ""

        return f"""
        <div class="strategy-info">
            <strong>Matching Strategy:</strong> {cfg.strategy.value}<br>
            <strong>IoU Threshold:</strong> {cfg.iou_threshold}<br>
            <strong>Coverage Threshold:</strong> {cfg.coverage_threshold}<br>
            <strong>Score Threshold:</strong> {cfg.score_threshold}
        </div>
        """

    def _build_metrics_table(self) -> str:
        rows = []
        for entity in self.result.entity_types:
            if entity == "O":
                continue
            if entity not in self.result.metrics:
                continue
            m = self.result.metrics[entity]
            rows.append(
                f"""
    <tr>
        <td><strong>{entity}</strong></td>
        <td>{m.precision:.3f}</td>
        <td>{m.recall:.3f}</td>
        <td>{m.f1:.3f}</td>
        <td>{m.tp}</td>
        <td>{m.fp}</td>
        <td>{m.fn}</td>
    </tr>
                """
            )

        return f"""
<table>
    <thead>
        <tr>
            <th>Entity Type</th>
            <th>Precision</th>
            <th>Recall</th>
            <th>F1 Score</th>
            <th>TP</th>
            <th>FP</th>
            <th>FN</th>
        </tr>
    </thead>
    <tbody>
        {''.join(rows)}
    </tbody>
</table>
        """

    def _build_error_summary(self) -> str:
        fp_count = len(self.result.errors.get("false_positives", []))
        fn_count = len(self.result.errors.get("false_negatives", []))
        partial_count = len(self.result.errors.get("partial_matches", []))

        return f"""
<ul>
    <li><strong>False Positives:</strong> {fp_count} total</li>
    <li><strong>False Negatives:</strong> {fn_count} total</li>
    <li><strong>Partial Matches:</strong> {partial_count} total</li>
</ul>
<p>View detailed error lists in: error_analysis_fps.csv, error_analysis_fns.csv</p>
        """

    def _embed_plot_as_base64(self, image_path: Path) -> str:
        if not image_path.exists():
            return ""

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return f"data:image/png;base64,{encoded}"
