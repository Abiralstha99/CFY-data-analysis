"""Uploaded CSVs and survey rows must stay in sync across replacements and deletes."""

from io import BytesIO

import pandas as pd

from cfy_pipeline import process_uploaded_file
from cfy_pipeline.schema import QuestionField, SurveySchema
from cfy_pipeline import storage


SCHEMA = SurveySchema(
    demographics=(),
    questions=(QuestionField("q_vaping_30day", "Vaping", "substance_use", (1, 5)),),
)


def upload(db_path, year: int, filename: str, content: bytes) -> None:
    source = BytesIO(content)
    source.name = filename
    process_uploaded_file(source, year, SCHEMA, db_path)


def test_uploaded_file_retains_exact_original_csv_after_refresh(tmp_path):
    db_path = tmp_path / "survey.db"
    original = b"q_vaping_30day,extra_note\n1,first\n7,second\n"

    upload(db_path, 2026, "raw_2026.csv", original)

    files = storage.list_survey_files(db_path)
    assert [(item.year, item.file_name, item.file_size, item.response_count) for item in files] == [
        (2026, "raw_2026.csv", len(original), 2)
    ]
    assert storage.load_original_file(db_path, 2026) == ("raw_2026.csv", original)
    assert storage.load_year(db_path, 2026)["q_vaping_30day"].tolist() == [1, 5]


def test_replacing_a_year_updates_file_and_rows_without_duplicating_years(tmp_path):
    db_path = tmp_path / "survey.db"
    upload(db_path, 2025, "old.csv", b"q_vaping_30day\n1\n2\n")
    upload(db_path, 2026, "other.csv", b"q_vaping_30day\n3\n")

    upload(db_path, 2025, "new.csv", b"q_vaping_30day\n4\n")

    assert [(item.year, item.response_count) for item in storage.list_survey_files(db_path)] == [
        (2026, 1), (2025, 1)
    ]
    assert storage.load_original_file(db_path, 2025) == ("new.csv", b"q_vaping_30day\n4\n")
    assert storage.load_year(db_path, 2025)["q_vaping_30day"].tolist() == [4]
    assert storage.load_year(db_path, 2026)["q_vaping_30day"].tolist() == [3]


def test_delete_removes_only_the_selected_year_and_its_original_file(tmp_path):
    db_path = tmp_path / "survey.db"
    upload(db_path, 2025, "old.csv", b"q_vaping_30day\n1\n")
    upload(db_path, 2026, "keep.csv", b"q_vaping_30day\n3\n")

    storage.delete_year_data(db_path, 2025)

    assert [(item.year, item.file_name) for item in storage.list_survey_files(db_path)] == [
        (2026, "keep.csv")
    ]
    assert storage.load_original_file(db_path, 2025) is None
    assert storage.load_year(db_path, 2025).empty
    assert storage.load_year(db_path, 2026)["q_vaping_30day"].tolist() == [3]


def test_existing_survey_rows_stay_visible_without_original_csv(tmp_path):
    db_path = tmp_path / "survey.db"
    storage.save_year_data(pd.DataFrame({"q_vaping_30day": [1, 2]}), 2024, db_path)

    files = storage.list_survey_files(db_path)

    assert len(files) == 1
    assert files[0].year == 2024
    assert files[0].response_count == 2
    assert files[0].has_original is False
    assert storage.load_original_file(db_path, 2024) is None
