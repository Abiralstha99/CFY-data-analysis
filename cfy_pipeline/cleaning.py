"""Data cleaning and validation against the survey schema.

Business rules (per PRD §6.2):
    - Missing columns: drop from analysis, don't fail the run. Flag in report.
    - Out-of-range Likert values: clip to valid range (not drop the row).
    - Invalid demographics: replace with "Unknown" (not drop the row).
"""

from __future__ import annotations

import dataclasses

import pandas as pd

from cfy_pipeline.schema import SurveySchema


@dataclasses.dataclass
class DataQualityReport:
    """Summary of all cleaning actions taken on a single upload.

    Shown to staff in the dashboard so they can sanity-check before trusting
    results. This is a PRD requirement (§6.2), not just a developer convenience.
    """

    dropped_columns: list[str]
    normalized_columns: dict[str, int]  # column name → count of values fixed
    row_count: int

    def has_issues(self) -> bool:
        return bool(self.dropped_columns) or bool(self.normalized_columns)


def _stringify_demographic_value(value: object) -> str:
    """Normalize a raw CSV cell to a string comparable to schema valid_values.

    Edge case: pandas read_csv infers numeric-looking demographics (e.g. grade
    "9") as int64 — or float64 when the column has NaN cells. So grade 9 may
    arrive as 9, 9.0, or NaN depending on the column. This function handles
    all three cases to produce consistent string comparisons.
    """
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def clean_dataframe(df: pd.DataFrame, schema: SurveySchema) -> tuple[pd.DataFrame, DataQualityReport]:
    """Validate and normalize a raw survey DataFrame against the schema.

    Returns the cleaned DataFrame (only schema-expected columns retained)
    and a quality report documenting all actions taken.
    """
    dropped_columns: list[str] = []
    normalized_columns: dict[str, int] = {}
    cleaned = df.copy()

    # --- Demographics: validate categorical values ---
    for demographic in schema.demographics:
        if demographic.name not in cleaned.columns:
            dropped_columns.append(demographic.name)
            continue
        cleaned[demographic.name] = cleaned[demographic.name].map(_stringify_demographic_value)
        invalid_mask = ~cleaned[demographic.name].isin(demographic.valid_values)
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            # Replace with "Unknown" rather than dropping rows — preserves sample size
            cleaned.loc[invalid_mask, demographic.name] = "Unknown"
            normalized_columns[demographic.name] = invalid_count

    # --- Questions: clip numeric values to valid Likert range ---
    for question in schema.questions:
        if question.name not in cleaned.columns:
            dropped_columns.append(question.name)
            continue
        low, high = question.valid_range
        out_of_range_mask = (cleaned[question.name] < low) | (cleaned[question.name] > high)
        out_of_range_count = int(out_of_range_mask.sum())
        if out_of_range_count:
            cleaned[question.name] = cleaned[question.name].clip(lower=low, upper=high)
            normalized_columns[question.name] = out_of_range_count

    # Only retain columns defined in the schema (drops any extra CSV columns)
    kept_columns = [c for c in schema.expected_columns() if c not in dropped_columns]
    cleaned = cleaned[kept_columns]

    report = DataQualityReport(
        dropped_columns=dropped_columns,
        normalized_columns=normalized_columns,
        row_count=len(cleaned),
    )
    return cleaned, report
