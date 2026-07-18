from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml


@dataclasses.dataclass(frozen=True)
class DemographicField:
    name: str
    valid_values: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class QuestionField:
    name: str
    label: str
    category: str
    valid_range: tuple[int, int]


@dataclasses.dataclass(frozen=True)
class SurveySchema:
    demographics: tuple[DemographicField, ...]
    questions: tuple[QuestionField, ...]

    def demographic_names(self) -> list[str]:
        return [d.name for d in self.demographics]

    def question_names(self) -> list[str]:
        return [q.name for q in self.questions]

    def expected_columns(self) -> list[str]:
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
