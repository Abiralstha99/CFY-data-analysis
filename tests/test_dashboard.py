"""Interaction checks for the Streamlit dashboard."""

from streamlit.testing.v1 import AppTest


def test_compare_years_shows_only_the_selected_question_chart():
    app = AppTest.from_string(
        """
import pandas as pd
from cfy_pipeline.dashboard import render_comparison_tab
from cfy_pipeline.schema import QuestionField, SurveySchema

schema = SurveySchema(
    demographics=(),
    questions=(
        QuestionField("q_vaping", "Vaping", "substance_use", (1, 5)),
        QuestionField("q_anxiety", "Anxiety", "mental_health", (1, 5)),
    ),
)
data = pd.DataFrame({
    "survey_year": [2024] * 4 + [2025] * 4,
    "q_vaping": [1, 2, 1, 2, 2, 3, 2, 3],
    "q_anxiety": [4, 3, 4, 3, 3, 2, 3, 2],
})
render_comparison_tab(data, schema)
"""
    ).run()

    assert not app.exception
    selector = next(box for box in app.selectbox if box.label == "Question to explore")
    assert len(app.get("plotly_chart")) == 1
    assert [heading.value for heading in app.subheader] == ["Vaping"]

    selector.select(selector.options[1]).run()

    assert not app.exception
    assert len(app.get("plotly_chart")) == 1
    assert [heading.value for heading in app.subheader] == ["Anxiety"]
