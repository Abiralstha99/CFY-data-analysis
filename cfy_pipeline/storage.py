from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

TABLE_NAME = "survey_responses"


def _table_exists(conn: sqlite3.Connection) -> bool:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,)
    )
    return cursor.fetchone() is not None


def save_year_data(df: pd.DataFrame, year: int, db_path: str | Path) -> None:
    to_write = df.copy()
    to_write["survey_year"] = year

    with sqlite3.connect(db_path) as conn:
        if _table_exists(conn):
            conn.execute(f"DELETE FROM {TABLE_NAME} WHERE survey_year = ?", (year,))
        to_write.to_sql(TABLE_NAME, conn, if_exists="append", index=False)


def load_all_years(db_path: str | Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn):
            return pd.DataFrame()
        return pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)


def load_year(db_path: str | Path, year: int) -> pd.DataFrame:
    all_years = load_all_years(db_path)
    if all_years.empty:
        return all_years
    return all_years[all_years["survey_year"] == year].reset_index(drop=True)
