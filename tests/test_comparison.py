import pandas as pd

from cfy_pipeline.comparison import compare_years
from cfy_pipeline.schema import QuestionField, SurveySchema


def make_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_compare_years_detects_significant_change():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 20 + [2025] * 20,
        "q_vaping_30day": [1] * 20 + [5] * 20,
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025)

    assert len(results) == 1
    result = results[0]
    assert result.question_name == "q_vaping_30day"
    assert result.significant is True
    assert result.current_year_mean > result.previous_mean


def test_compare_years_reports_not_significant_for_similar_years():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 20 + [2025] * 20,
        "q_vaping_30day": ([1, 2] * 10) + ([1, 2] * 10),
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025)

    assert results[0].significant is False


def test_compare_years_by_group_splits_results_per_subgroup():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 20 + [2025] * 20,
        "grade": (["9"] * 10 + ["10"] * 10) * 2,
        "q_vaping_30day": [1] * 20 + [5] * 20,
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025, group_by="grade")

    groups = {r.group for r in results}
    assert groups == {"9", "10"}


def test_compare_years_skips_question_with_insufficient_sample_size():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024, 2025],
        "q_vaping_30day": [1, 2],
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025)

    assert results == []
