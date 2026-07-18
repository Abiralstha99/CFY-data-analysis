from __future__ import annotations

import dataclasses

import pandas as pd

from cfy_pipeline.schema import SurveySchema


@dataclasses.dataclass
class DataQualityReport:
    dropped_columns: list[str]
    normalized_columns: dict[str, int]
    row_count: int

    def has_issues(self) -> bool:
        return bool(self.dropped_columns) or bool(self.normalized_columns)


def _stringify_demographic_value(value: object) -> str:
    """Render a raw demographic cell as a string comparable to schema valid_values.

    read_csv infers numeric-looking demographics (e.g. grade) as int64 — or
    float64 when the column has blanks — so "9" arrives as 9 or 9.0. Integral
    floats are formatted without the trailing ".0"; missing values become ""
    so downstream validation maps them to "Unknown".
    """
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def clean_dataframe(df: pd.DataFrame, schema: SurveySchema) -> tuple[pd.DataFrame, DataQualityReport]:
    dropped_columns: list[str] = []
    normalized_columns: dict[str, int] = {}
    cleaned = df.copy()

    for demographic in schema.demographics:
        if demographic.name not in cleaned.columns:
            dropped_columns.append(demographic.name)
            continue
        cleaned[demographic.name] = cleaned[demographic.name].map(_stringify_demographic_value)
        invalid_mask = ~cleaned[demographic.name].isin(demographic.valid_values)
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            cleaned.loc[invalid_mask, demographic.name] = "Unknown"
            normalized_columns[demographic.name] = invalid_count

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

    kept_columns = [c for c in schema.expected_columns() if c not in dropped_columns]
    cleaned = cleaned[kept_columns]

    report = DataQualityReport(
        dropped_columns=dropped_columns,
        normalized_columns=normalized_columns,
        row_count=len(cleaned),
    )
    return cleaned, report
