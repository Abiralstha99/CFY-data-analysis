from __future__ import annotations

from pathlib import Path

import pandas as pd

from cfy_pipeline.cleaning import DataQualityReport, clean_dataframe
from cfy_pipeline.schema import SurveySchema
from cfy_pipeline.storage import save_year_data


def process_uploaded_file(
    csv_source,
    year: int,
    schema: SurveySchema,
    db_path: str | Path,
) -> DataQualityReport:
    df = pd.read_csv(csv_source)
    cleaned, report = clean_dataframe(df, schema)
    save_year_data(cleaned, year, db_path)
    return report
