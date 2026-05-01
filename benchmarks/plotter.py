"""PII Evaluation Result Visualization.

Generates plots from EvaluationResult objects:
  - Confusion matrix heatmap (matplotlib + plotly)
  - Per-entity metrics bar charts (plotly)
  - Error distribution plots (plotly)
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

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import seaborn as sns
from benchmarks.evaluator import EvaluationResult


class EvaluationPlotter:
    """Generate visualization artifacts from EvaluationResult."""

    def __init__(self, result: EvaluationResult, output_dir: Path) -> None:
        """Initialize plotter.

        Args:
            result: EvaluationResult object with metrics and errors
            output_dir: Directory where plots will be saved
        """
        self.result = result
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir = self.output_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)

    def plot_confusion_matrix_heatmap(self) -> tuple[Path, Path]:
        """Generate confusion matrix heatmaps (matplotlib PNG + plotly HTML).

        Returns:
            Tuple of (png_path, html_path)
        """
        matrix = self.result.confusion_matrix
        entities = self.result.entity_types

        # 1. Matplotlib version (PNG)
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
        plt.title("Confusion Matrix: Predicted vs Ground Truth Entities")
        plt.xlabel("Predicted Entity Type")
        plt.ylabel("Ground Truth Entity Type")
        plt.tight_layout()

        png_path = self.plots_dir / "confusion_matrix.png"
        plt.savefig(png_path, dpi=150, bbox_inches="tight")
        plt.close()

        # 2. Plotly version (Interactive HTML)
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
            title="Confusion Matrix: Predicted vs Ground Truth Entities",
            xaxis_title="Predicted Entity Type",
            yaxis_title="Ground Truth Entity Type",
            width=800,
            height=700,
        )

        html_path = self.plots_dir / "confusion_matrix.html"
        fig.write_html(str(html_path))

        return png_path, html_path

    def plot_metrics_bars(self) -> Path:
        """Generate per-entity metrics bar chart (precision/recall/F1).

        Returns:
            Path to generated HTML file
        """
        metrics_data = {
            "Entity": [],
            "Precision": [],
            "Recall": [],
            "F1": [],
        }

        for entity in self.result.entity_types:
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

        fig.update_layout(
            title="Per-Entity Metrics: Precision, Recall, F1",
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
        """Generate FP/FN error distribution by entity type.

        Returns:
            Path to generated HTML file
        """
        error_data = {"Entity": [], "False Positives": [], "False Negatives": []}

        for entity in self.result.entity_types:
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

    def generate_html_report(self) -> Path:
        """Generate single-page HTML report with all key metrics and plots.

        Returns:
            Path to generated HTML file
        """
        # Prepare metrics summary
        metrics_html = self._build_metrics_table()
        error_summary = self._build_error_summary()

        # Prepare plot embeds (base64 PNG)
        confusion_matrix_b64 = self._embed_plot_as_base64(self.plots_dir / "confusion_matrix.png")

        # Build HTML
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
        <h1>📊 PII Detection Evaluation Report</h1>
        
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

    def _build_metrics_table(self) -> str:
        """Build HTML table of per-entity metrics.

        Returns:
            HTML table string
        """
        rows = []
        for entity in self.result.entity_types:
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
        """Build HTML summary of errors.

        Returns:
            HTML string with error counts
        """
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
        """Encode image as base64 for embedding in HTML.

        Args:
            image_path: Path to PNG image

        Returns:
            Base64-encoded data URL
        """
        import base64

        if not image_path.exists():
            return ""

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return f"data:image/png;base64,{encoded}"
