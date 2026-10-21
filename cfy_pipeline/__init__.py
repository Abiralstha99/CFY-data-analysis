"""CFY Youth Survey analysis pipeline.

See docs/architecture.md for system design and module responsibilities.

Public API:
    process_uploaded_file — clean a CSV and persist it to the survey database.
    load_schema — load a survey schema from a YAML config file.
    SurveySchema, DataQualityReport — core data classes.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from cfy_pipeline.cleaning import DataQualityReport, clean_dataframe
from cfy_pipeline.schema import SurveySchema, load_schema
from cfy_pipeline.storage import save_uploaded_year_data

__all__ = [
    "DataQualityReport",
    "SurveySchema",
    "load_schema",
    "process_uploaded_file",
]


def process_uploaded_file(
    csv_source,
    year: int,
    schema: SurveySchema,
    db_path: str | Path,
) -> DataQualityReport:
    """Clean a raw survey CSV and persist the results for the given year.

    Idempotent per year: re-uploading the same year replaces previous data.
    Returns the quality report so the UI can show what was cleaned/dropped.
    """
    if isinstance(csv_source, (str, Path)):
        path = Path(csv_source)
        original_csv = path.read_bytes()
        file_name = path.name
    else:
        if hasattr(csv_source, "seek"):
            csv_source.seek(0)
        original_csv = csv_source.read()
        if isinstance(original_csv, str):
            original_csv = original_csv.encode("utf-8")
        file_name = str(getattr(csv_source, "name", f"survey_{year}.csv"))
        file_name = file_name.replace("\\", "/").split("/")[-1]

    df = pd.read_csv(BytesIO(original_csv))
    cleaned, report = clean_dataframe(df, schema)
    save_uploaded_year_data(cleaned, year, db_path, file_name, original_csv)
    return report
