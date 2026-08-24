"""Year-over-year statistical comparison of survey metrics.

Uses Welch's t-test (unequal variance, unpaired) to compare question means
between two years. Requires ≥2 responses per group per year; smaller groups
are silently skipped.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
from scipy import stats

from cfy_pipeline.schema import SurveySchema

SIGNIFICANCE_THRESHOLD = 0.05


@dataclasses.dataclass
class ComparisonResult:
    question_name: str
    group: str          # "All" for county-wide, or a demographic value like "9"
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
    """Compare question means between two years using Welch's t-test.

    When group_by is provided (a demographic column name), results are split
    per subgroup value. When None, computes county-wide comparison only.
    """
    results: list[ComparisonResult] = []
    groups = _resolve_groups(df_all, group_by)

    for question in schema.questions:
        for group in groups:
            subset = _filter_group(df_all, group_by, group)
            prev = subset.loc[subset["survey_year"] == previous_year, question.name].dropna()
            curr = subset.loc[subset["survey_year"] == current_year, question.name].dropna()

            if len(prev) < 2 or len(curr) < 2:
                continue

            _t, p_value = stats.ttest_ind(curr, prev, equal_var=False)
            results.append(
                ComparisonResult(
                    question_name=question.name,
                    group=group,
                    previous_year=previous_year,
                    current_year=current_year,
                    previous_mean=float(prev.mean()),
                    current_year_mean=float(curr.mean()),
                    p_value=float(p_value),
                    # bool() ensures native Python bool, not numpy.bool_ (breaks `is True` assertions)
                    significant=bool(p_value < SIGNIFICANCE_THRESHOLD),
                )
            )

    return results


def _resolve_groups(df: pd.DataFrame, group_by: str | None) -> list[str]:
    """Return the list of group labels to iterate over."""
    if group_by is None:
        return ["All"]
    return sorted(df[group_by].dropna().unique().tolist())


def _filter_group(df: pd.DataFrame, group_by: str | None, group: str) -> pd.DataFrame:
    """Subset the DataFrame to a single demographic group."""
    if group_by is None:
        return df
    return df[df[group_by] == group]
