"""Multi-year directional trend detection via linear regression.

Fits a linear regression to yearly question means. A trend is "sustained" if
the slope is significantly non-zero (p < 0.05). Requires ≥3 years of data.

Limitations:
    - Assumes linearity — non-linear patterns will be missed.
    - With exactly 3 years, a single outlier year can drive significance.
"""

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
    group: str           # "All" for county-wide, or a demographic subgroup value
    years: list[int]
    yearly_means: list[float]
    slope: float         # Mean score change per year (Likert units/year)
    p_value: float
    is_sustained: bool

    @property
    def direction(self) -> str:
        """Human-readable trend direction for display in charts/tables."""
        if not self.is_sustained:
            return "none"
        return "increasing" if self.slope > 0 else "decreasing"


def detect_multi_year_trends(
    df_all: pd.DataFrame,
    schema: SurveySchema,
    group_by: str | None = None,
) -> list[TrendResult]:
    """Detect sustained directional trends across 3+ years of data.

    Uses scipy.stats.linregress on (year, mean_score) pairs. When group_by is
    provided, trends are computed independently per subgroup value.
    """
    results: list[TrendResult] = []
    groups = _resolve_groups(df_all, group_by)

    for question in schema.questions:
        for group in groups:
            subset = _filter_group(df_all, group_by, group)
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
