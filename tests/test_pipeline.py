import pandas as pd

from cfy_pipeline.pipeline import process_uploaded_file
from cfy_pipeline.schema import QuestionField, SurveySchema
from cfy_pipeline.storage import load_year


def make_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_process_uploaded_file_cleans_and_persists_data(tmp_path):
    schema = make_schema()
    csv_path = tmp_path / "survey_2025.csv"
    pd.DataFrame({"q_vaping_30day": [1, 7, 3]}).to_csv(csv_path, index=False)
    db_path = tmp_path / "survey.db"

    report = process_uploaded_file(csv_path, 2025, schema, db_path)

    assert report.normalized_columns["q_vaping_30day"] == 1
    stored = load_year(db_path, 2025)
    assert stored["q_vaping_30day"].tolist() == [1, 5, 3]
