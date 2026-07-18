from pathlib import Path

from cfy_pipeline.schema import load_schema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "survey_schema.yaml"


def test_load_schema_parses_demographics_and_questions():
    schema = load_schema(SCHEMA_PATH)

    assert "grade" in schema.demographic_names()
    assert "gender" in schema.demographic_names()
    assert "q_vaping_30day" in schema.question_names()

    vaping = schema.question_by_name("q_vaping_30day")
    assert vaping.category == "substance_use"
    assert vaping.valid_range == (1, 5)

    grade = schema.demographic_by_name("grade")
    assert "9" in grade.valid_values


def test_expected_columns_combines_demographics_and_questions():
    schema = load_schema(SCHEMA_PATH)
    expected = schema.expected_columns()

    assert "grade" in expected
    assert "q_mh_anxiety" in expected
    assert len(expected) == len(schema.demographics) + len(schema.questions)
