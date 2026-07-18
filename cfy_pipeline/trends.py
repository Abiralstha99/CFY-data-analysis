from __future__ import annotations

import dataclasses

import pandas as pd
from scipy import stats

from cfy_pipeline.schema import SurveySchema

MIN_YEARS_FOR_TREND = 3
TREND_SIGNIFICANCE_THRESHOLD = 0.05


@dataclasses.dataclass
class TrendResult:
    question_name: str
    group: str
    years: list[int]
    yearly_means: list[float]
    slope: float
    p_value: float
    is_sustained: bool

    @property
    def direction(self) -> str:
        if not self.is_sustained:
            return "none"
        return "increasing" if self.slope > 0 else "decreasing"


def detect_multi_year_trends(
    df_all: pd.DataFrame,
    schema: SurveySchema,
    group_by: str | None = None,
) -> list[TrendResult]:
    results: list[TrendResult] = []

    groups = ["All"]
    if group_by is not None:
        groups = sorted(df_all[group_by].dropna().unique().tolist())

    for question in schema.questions:
        for group in groups:
            if group_by is None or group == "All":
                subset = df_all
            else:
                subset = df_all[df_all[group_by] == group]

            yearly = (
                subset.dropna(subset=[question.name])
                .groupby("survey_year")[question.name]
                .mean()
                .sort_index()
            )

            if len(yearly) < MIN_YEARS_FOR_TREND:
                continue

            years = yearly.index.tolist()
            means = yearly.values.tolist()
            slope, _intercept, _r, p_value, _stderr = stats.linregress(years, means)

            results.append(
                TrendResult(
                    question_name=question.name,
                    group=group,
                    years=years,
                    yearly_means=means,
                    slope=float(slope),
                    p_value=float(p_value),
                    is_sustained=bool(p_value < TREND_SIGNIFICANCE_THRESHOLD),
                )
            )

    return results
