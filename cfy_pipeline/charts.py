"""Plotly figure builders for the dashboard.

Stateless: each function takes analysis results → returns a Figure. No I/O.

Color system (CVD-safe, WCAG ≥3:1 contrast):
    Red  = statistically significant (action needed)
    Blue = no significant change (baseline)
    Gray = previous-year reference bars (context)
"""

from __future__ import annotations

import plotly.graph_objects as go

from cfy_pipeline.comparison import ComparisonResult
from cfy_pipeline.trends import TrendResult

SIGNIFICANT_COLOR = "#d03b3b"
BASELINE_COLOR = "#2a78d6"
PREVIOUS_YEAR_COLOR = "#898781"

# All survey questions use 1–5 Likert scale; axis range gives breathing room
_LIKERT_AXIS_RANGE = [0, 5.5]


def build_comparison_figure(results: list[ComparisonResult], question_label: str) -> go.Figure:
    """Grouped bar chart: previous year (gray) vs current year (red/blue by significance)."""
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
        hovertemplate="%{x}<br>Previous mean: %{y:.2f}<extra></extra>",
    )
    fig.add_bar(
        name="Current Year",
        x=groups,
        y=current_means,
        marker_color=colors,
        customdata=p_values,
        hovertemplate="%{x}<br>Current mean: %{y:.2f}<br>p-value: %{customdata:.4f}<extra></extra>",
    )
    fig.update_layout(
        barmode="group",
        title=question_label,
        xaxis_title="Group",
        yaxis_title="Mean Score",
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
        hovertemplate="%{x}<br>Mean: %{y:.2f}<extra></extra>",
    )
    fig.update_layout(
        title=f"{question_label} — {result.group} ({result.direction})",
        xaxis_title="Year",
        yaxis_title="Mean Score",
        yaxis_range=_LIKERT_AXIS_RANGE,
        xaxis=dict(tickmode="array", tickvals=result.years),
    )
    return fig
