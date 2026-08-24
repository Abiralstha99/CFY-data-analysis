"""Survey schema definition and YAML loader.

Design decision: frozen dataclasses rather than dicts so that schema objects are
hashable and immutable once loaded — prevents accidental mutation during a run.

To add a new question or demographic field, edit config/survey_schema.yaml.
No code changes required unless the field type is fundamentally new.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml


@dataclasses.dataclass(frozen=True)
class DemographicField:
    name: str
    # All valid values stored as strings — even numeric grades like "9" —
    # because CSV parsing may yield mixed types (see cleaning._stringify_demographic_value).
    valid_values: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class QuestionField:
    name: str
    label: str        # Human-readable label for chart titles
    category: str     # Grouping key (e.g. "substance_use", "mental_health")
    valid_range: tuple[int, int]  # Inclusive Likert scale bounds


@dataclasses.dataclass(frozen=True)
class SurveySchema:
    demographics: tuple[DemographicField, ...]
    questions: tuple[QuestionField, ...]

    def demographic_names(self) -> list[str]:
        return [d.name for d in self.demographics]

    def question_names(self) -> list[str]:
        return [q.name for q in self.questions]

    def expected_columns(self) -> list[str]:
        """All columns a fully-conforming CSV should contain."""
        return self.demographic_names() + self.question_names()

    def question_by_name(self, name: str) -> QuestionField:
        for q in self.questions:
            if q.name == name:
                return q
        raise KeyError(f"Unknown question field: {name}")

    def demographic_by_name(self, name: str) -> DemographicField:
        for d in self.demographics:
            if d.name == name:
                return d
        raise KeyError(f"Unknown demographic field: {name}")


def load_schema(path: str | Path) -> SurveySchema:
    """Parse a survey schema YAML file into a SurveySchema instance.

    Expected YAML structure:
        demographics:
          - name: grade
            valid_values: ["6", "7", ...]
        questions:
          - name: q_vaping_30day
            label: "Vaping frequency (past 30 days)"
            category: substance_use
            valid_range: [1, 5]
    """
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    demographics = tuple(
        DemographicField(name=d["name"], valid_values=tuple(d["valid_values"]))
        for d in raw["demographics"]
    )
    questions = tuple(
        QuestionField(
            name=q["name"],
            label=q["label"],
            category=q["category"],
            valid_range=tuple(q["valid_range"]),
        )
        for q in raw["questions"]
    )
    return SurveySchema(demographics=demographics, questions=questions)
