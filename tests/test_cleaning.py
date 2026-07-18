import pandas as pd

from cfy_pipeline.cleaning import clean_dataframe
from cfy_pipeline.schema import DemographicField, QuestionField, SurveySchema


def make_test_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(
            DemographicField(name="grade", valid_values=("9", "10", "11", "12")),
        ),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_clean_dataframe_drops_missing_expected_column():
    schema = make_test_schema()
    df = pd.DataFrame({"grade": ["9", "10"]})

    cleaned, report = clean_dataframe(df, schema)

    assert "q_vaping_30day" not in cleaned.columns
    assert report.dropped_columns == ["q_vaping_30day"]


def test_clean_dataframe_normalizes_out_of_range_likert_values():
    schema = make_test_schema()
    df = pd.DataFrame({
        "grade": ["9", "10", "11"],
        "q_vaping_30day": [1, 7, -2],
    })

    cleaned, report = clean_dataframe(df, schema)

    assert cleaned["q_vaping_30day"].tolist() == [1, 5, 1]
    assert report.normalized_columns["q_vaping_30day"] == 2


def test_clean_dataframe_normalizes_invalid_categorical_value():
    schema = make_test_schema()
    df = pd.DataFrame({
        "grade": ["9", "13"],
        "q_vaping_30day": [1, 2],
    })

    cleaned, report = clean_dataframe(df, schema)

    assert cleaned["grade"].tolist() == ["9", "Unknown"]
    assert report.normalized_columns["grade"] == 1


def test_clean_dataframe_reports_row_count():
    schema = make_test_schema()
    df = pd.DataFrame({
        "grade": ["9", "10"],
        "q_vaping_30day": [1, 2],
    })

    _, report = clean_dataframe(df, schema)

    assert report.row_count == 2


def test_has_issues_false_when_data_is_clean():
    schema = make_test_schema()
    df = pd.DataFrame({"grade": ["9"], "q_vaping_30day": [1]})

    _, report = clean_dataframe(df, schema)

    assert report.has_issues() is False
