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


def test_question_scale_wording_loads_when_configured(tmp_path):
    config = tmp_path / "schema.yaml"
    config.write_text(
        "demographics: []\nquestions:\n"
        "  - name: q_example\n"
        "    label: Example question\n"
        "    category: example\n"
        "    valid_range: [1, 5]\n"
        "    low_label: Never\n"
        "    high_label: Always\n"
        "    interpretation: Higher scores mean more frequent responses.\n"
    )

    question = load_schema(config).questions[0]

    assert question.low_label == "Never"
    assert question.high_label == "Always"
    assert question.interpretation == "Higher scores mean more frequent responses."
