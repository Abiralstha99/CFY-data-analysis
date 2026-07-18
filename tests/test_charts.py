from cfy_pipeline.charts import build_comparison_figure, build_trend_figure
from cfy_pipeline.comparison import ComparisonResult
from cfy_pipeline.trends import TrendResult


def test_build_comparison_figure_marks_significant_bar_red():
    results = [
        ComparisonResult(
            question_name="q_vaping_30day",
            group="9",
            previous_year=2024,
            current_year=2025,
            previous_mean=1.0,
            current_year_mean=4.0,
            p_value=0.001,
            significant=True,
        )
    ]

    fig = build_comparison_figure(results, "Vaping frequency")

    assert len(fig.data) == 2
    assert fig.data[1].marker.color[0] == "crimson"


def test_build_trend_figure_colors_sustained_trend_red():
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

    assert fig.data[0].line.color == "crimson"
    assert "increasing" in fig.layout.title.text
