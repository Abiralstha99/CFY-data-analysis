import pandas as pd

from cfy_pipeline.schema import QuestionField, SurveySchema
from cfy_pipeline.trends import detect_multi_year_trends


def make_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_detect_multi_year_trends_flags_sustained_increase():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2022] * 10 + [2023] * 10 + [2024] * 10 + [2025] * 10,
        "q_vaping_30day": [1] * 10 + [2] * 10 + [3] * 10 + [4] * 10,
    })

    results = detect_multi_year_trends(df, schema)

    assert len(results) == 1
    result = results[0]
    assert result.is_sustained is True
    assert result.direction == "increasing"
    assert result.years == [2022, 2023, 2024, 2025]


def test_detect_multi_year_trends_skips_when_fewer_than_min_years():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 10 + [2025] * 10,
        "q_vaping_30day": [1] * 10 + [4] * 10,
    })

    results = detect_multi_year_trends(df, schema)

    assert results == []


def test_detect_multi_year_trends_reports_none_direction_when_not_sustained():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2022] * 10 + [2023] * 10 + [2024] * 10,
        "q_vaping_30day": (
            [2, 3, 2, 3, 2, 3, 2, 3, 2, 3]
            + [3, 2, 3, 2, 3, 2, 3, 2, 3, 2]
            + [2, 3, 2, 3, 2, 3, 2, 3, 2, 3]
        ),
    })

    results = detect_multi_year_trends(df, schema)

    assert len(results) == 1
    assert results[0].is_sustained is False
    assert results[0].direction == "none"


def test_detect_multi_year_trends_by_group_splits_per_subgroup():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2022] * 20 + [2023] * 20 + [2024] * 20,
        "grade": (["9"] * 10 + ["10"] * 10) * 3,
        "q_vaping_30day": [1] * 10 + [1] * 10 + [2] * 10 + [2] * 10 + [3] * 10 + [3] * 10,
    })

    results = detect_multi_year_trends(df, schema, group_by="grade")

    groups = {r.group for r in results}
    assert groups == {"9", "10"}
