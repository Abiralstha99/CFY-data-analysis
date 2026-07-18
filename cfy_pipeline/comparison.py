from __future__ import annotations

import dataclasses

import pandas as pd
from scipy import stats

from cfy_pipeline.schema import SurveySchema

SIGNIFICANCE_THRESHOLD = 0.05


@dataclasses.dataclass
class ComparisonResult:
    question_name: str
    group: str
    previous_year: int
    current_year: int
    previous_mean: float
    current_year_mean: float
    p_value: float
    significant: bool


def compare_years(
    df_all: pd.DataFrame,
    schema: SurveySchema,
    previous_year: int,
    current_year: int,
    group_by: str | None = None,
) -> list[ComparisonResult]:
    results: list[ComparisonResult] = []

    groups = ["All"]
    if group_by is not None:
        groups = sorted(df_all[group_by].dropna().unique().tolist())

    for question in schema.questions:
        for group in groups:
            if group_by is None or group == "All":
                subset = df_all
            else:
                subset = df_all[df_all[group_by] == group]

            previous_values = subset.loc[subset["survey_year"] == previous_year, question.name].dropna()
            current_values = subset.loc[subset["survey_year"] == current_year, question.name].dropna()

            if len(previous_values) < 2 or len(current_values) < 2:
                continue

            _t_stat, p_value = stats.ttest_ind(current_values, previous_values, equal_var=False)

            results.append(
                ComparisonResult(
                    question_name=question.name,
                    group=group,
                    previous_year=previous_year,
                    current_year=current_year,
                    previous_mean=float(previous_values.mean()),
                    current_year_mean=float(current_values.mean()),
                    p_value=float(p_value),
                    significant=bool(p_value < SIGNIFICANCE_THRESHOLD),
                )
            )

    return results
