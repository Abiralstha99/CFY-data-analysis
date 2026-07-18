from cfy_pipeline.charts import (
    BASELINE_COLOR,
    SIGNIFICANT_COLOR,
    build_comparison_figure,
    build_trend_figure,
)
from cfy_pipeline.comparison import ComparisonResult
from cfy_pipeline.trends import TrendResult


def make_comparison_result(significant: bool) -> ComparisonResult:
    return ComparisonResult(
        question_name="q_vaping_30day",
        group="9",
        previous_year=2024,
        current_year=2025,
        previous_mean=1.0,
        current_year_mean=4.0,
        p_value=0.001 if significant else 0.5,
        significant=significant,
    )


def test_build_comparison_figure_marks_significant_bar_with_alert_color():
    fig = build_comparison_figure([make_comparison_result(significant=True)], "Vaping frequency")

    assert len(fig.data) == 2
    assert fig.data[1].marker.color[0] == SIGNIFICANT_COLOR


def test_build_comparison_figure_uses_baseline_color_when_not_significant():
    fig = build_comparison_figure([make_comparison_result(significant=False)], "Vaping frequency")

    assert fig.data[1].marker.color[0] == BASELINE_COLOR


def test_build_trend_figure_colors_sustained_trend_with_alert_color():
    result = TrendResult(
        question_name="q_vaping_30day",
        group="All",
        years=[2022, 2023, 2024],
        yearly_means=[1.0, 2.0, 3.0],
        slope=1.0,
        p_value=0.01,
        is_sustained=True,
    )

    fig = build_trend_figure(result, "Vaping frequency")

    assert fig.data[0].line.color == SIGNIFICANT_COLOR
    assert "increasing" in fig.layout.title.text
