"""Lightweight SQLite persistence for cleaned survey data.

Upsert semantics: re-uploading a year deletes then re-inserts, so staff
can correct a bad upload without manual DB surgery.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

_TABLE = "survey_responses"

# SQL uses the constant table name directly (not parameterized) because SQLite
# doesn't support parameterized identifiers. Safe: _TABLE is a module constant.
_TABLE_EXISTS_SQL = (
    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
)
_DELETE_YEAR_SQL = f"DELETE FROM {_TABLE} WHERE survey_year = ?"
_SELECT_ALL_SQL = f"SELECT * FROM {_TABLE}"


def _table_exists(conn: sqlite3.Connection) -> bool:
    return conn.execute(_TABLE_EXISTS_SQL, (_TABLE,)).fetchone() is not None


def save_year_data(df: pd.DataFrame, year: int, db_path: str | Path) -> None:
    """Persist a cleaned DataFrame for one survey year (upsert semantics).

    If data for this year already exists, it is fully replaced. The table is
    auto-created on first insert via pandas to_sql.
    """
    to_write = df.copy()
    to_write["survey_year"] = year

    with sqlite3.connect(db_path) as conn:
        if _table_exists(conn):
            conn.execute(_DELETE_YEAR_SQL, (year,))
        to_write.to_sql(_TABLE, conn, if_exists="append", index=False)


def load_all_years(db_path: str | Path) -> pd.DataFrame:
    """Load every stored survey year into a single DataFrame.

    Used by comparison and trend modules that need the full history.
    Returns an empty DataFrame if the DB or table doesn't exist yet.
    """
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn):
            return pd.DataFrame()
        return pd.read_sql(_SELECT_ALL_SQL, conn)


def load_year(db_path: str | Path, year: int) -> pd.DataFrame:
    """Load a single survey year's data (used for preview after upload)."""
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn):
            return pd.DataFrame()
        return pd.read_sql(
            f"{_SELECT_ALL_SQL} WHERE survey_year = ?", conn, params=(year,)
        )
