from __future__ import annotations

import plotly.graph_objects as go

from cfy_pipeline.comparison import ComparisonResult
from cfy_pipeline.trends import TrendResult


def build_comparison_figure(results: list[ComparisonResult], question_label: str) -> go.Figure:
    groups = [r.group for r in results]
    previous_means = [r.previous_mean for r in results]
    current_means = [r.current_year_mean for r in results]
    colors = ["crimson" if r.significant else "steelblue" for r in results]

    fig = go.Figure()
    fig.add_bar(name="Previous Year", x=groups, y=previous_means, marker_color="lightgray")
    fig.add_bar(name="Current Year", x=groups, y=current_means, marker_color=colors)
    fig.update_layout(barmode="group", title=question_label, xaxis_title="Group", yaxis_title="Mean Score")
    return fig


def build_trend_figure(result: TrendResult, question_label: str) -> go.Figure:
    fig = go.Figure()
    line_color = "crimson" if result.is_sustained else "steelblue"
    fig.add_scatter(x=result.years, y=result.yearly_means, mode="lines+markers", line_color=line_color)
    fig.update_layout(
        title=f"{question_label} — {result.group} ({result.direction})",
        xaxis_title="Year",
        yaxis_title="Mean Score",
    )
    return fig
