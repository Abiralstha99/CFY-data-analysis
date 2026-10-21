"""Plotly figure builders for the dashboard.

Stateless: each function takes analysis results → returns a Figure. No I/O.

Color system for the dark dashboard:
    Coral = statistically flagged change
    Blue  = no flagged change
    Gray  = previous-year reference bars
"""

from __future__ import annotations

import plotly.graph_objects as go

from cfy_pipeline.comparison import ComparisonResult
from cfy_pipeline.trends import TrendResult

SIGNIFICANT_COLOR = "#F28C7E"
BASELINE_COLOR = "#78B7E8"
PREVIOUS_YEAR_COLOR = "#8FA4B8"

# All survey questions use 1–5 Likert scale; axis range gives breathing room
_LIKERT_AXIS_RANGE = [0, 5.5]


def build_comparison_figure(results: list[ComparisonResult], question_label: str) -> go.Figure:
    """Grouped bar chart: previous year (gray) vs current year (coral/blue)."""
    groups = [r.group for r in results]
    previous_means = [r.previous_mean for r in results]
    current_means = [r.current_year_mean for r in results]
    colors = [SIGNIFICANT_COLOR if r.significant else BASELINE_COLOR for r in results]
    p_values = [r.p_value for r in results]

    fig = go.Figure()
    fig.add_bar(
        name="Previous Year",
        x=groups,
        y=previous_means,
        marker_color=PREVIOUS_YEAR_COLOR,
        customdata=[r.previous_count for r in results],
        hovertemplate="%{x}<br>Previous average: %{y:.2f}<br>Responses: %{customdata}<extra></extra>",
    )
    fig.add_bar(
        name="Current Year",
        x=groups,
        y=current_means,
        marker_color=colors,
        customdata=[[r.current_count, p] for r, p in zip(results, p_values)],
        hovertemplate="%{x}<br>Current average: %{y:.2f}<br>Responses: %{customdata[0]}<br>p-value: %{customdata[1]:.4f}<extra></extra>",
    )
    fig.update_layout(
        barmode="group",
        title=question_label,
        xaxis_title="Group",
        yaxis_title="Average response (1–5)",
        yaxis_range=_LIKERT_AXIS_RANGE,
    )
    return fig


def build_trend_figure(result: TrendResult, question_label: str) -> go.Figure:
    """Line chart showing yearly means with color indicating sustained trend."""
    fig = go.Figure()
    line_color = SIGNIFICANT_COLOR if result.is_sustained else BASELINE_COLOR
    fig.add_scatter(
        x=result.years,
        y=result.yearly_means,
        mode="lines+markers",
        line_color=line_color,
        marker_size=8,
        customdata=result.yearly_counts or [None] * len(result.years),
        hovertemplate="%{x}<br>Average response: %{y:.2f}<br>Responses: %{customdata}<extra></extra>",
    )
    fig.update_layout(
        title=f"{question_label} — {result.group} ({result.direction})",
        xaxis_title="Year",
        yaxis_title="Average response (1–5)",
        yaxis_range=_LIKERT_AXIS_RANGE,
        xaxis=dict(tickmode="array", tickvals=result.years),
    )
    return fig
