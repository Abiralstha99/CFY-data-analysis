"""SQLite storage for cleaned survey responses and their original CSV files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pandas as pd

_RESPONSES_TABLE = "survey_responses"
_FILES_TABLE = "uploaded_files"


@dataclass(frozen=True)
class SurveyFile:
    year: int
    file_name: str
    uploaded_at: str | None
    file_size: int | None
    response_count: int
    has_original: bool


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    ).fetchone() is not None


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _column_type(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    return "TEXT"


def _database_value(value):
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def _replace_response_rows(conn: sqlite3.Connection, df: pd.DataFrame, year: int) -> None:
    """Replace one year inside the caller's transaction, expanding columns as needed."""
    to_write = df.copy()
    to_write["survey_year"] = year
    columns = to_write.columns.tolist()

    if not _table_exists(conn, _RESPONSES_TABLE):
        definitions = [
            f"{_quote_identifier(name)} {_column_type(to_write[name])}"
            for name in columns
        ]
        conn.execute(f"CREATE TABLE {_RESPONSES_TABLE} ({', '.join(definitions)})")
    else:
        existing = {
            row[1] for row in conn.execute(f"PRAGMA table_info({_RESPONSES_TABLE})")
        }
        for name in columns:
            if name not in existing:
                conn.execute(
                    f"ALTER TABLE {_RESPONSES_TABLE} ADD COLUMN "
                    f"{_quote_identifier(name)} {_column_type(to_write[name])}"
                )

    conn.execute(f"DELETE FROM {_RESPONSES_TABLE} WHERE survey_year = ?", (year,))
    placeholders = ", ".join("?" for _ in columns)
    names = ", ".join(_quote_identifier(name) for name in columns)
    conn.executemany(
        f"INSERT INTO {_RESPONSES_TABLE} ({names}) VALUES ({placeholders})",
        [tuple(_database_value(value) for value in row) for row in to_write.itertuples(index=False, name=None)],
    )


def _ensure_file_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_FILES_TABLE} ("
        "survey_year INTEGER PRIMARY KEY, "
        "file_name TEXT NOT NULL, "
        "uploaded_at TEXT NOT NULL, "
        "file_size INTEGER NOT NULL, "
        "content BLOB NOT NULL)"
    )


def save_year_data(df: pd.DataFrame, year: int, db_path: str | Path) -> None:
    """Replace cleaned rows for a year without claiming to retain an original CSV."""
    with sqlite3.connect(db_path) as conn:
        with conn:
            _replace_response_rows(conn, df, year)
            if _table_exists(conn, _FILES_TABLE):
                conn.execute(f"DELETE FROM {_FILES_TABLE} WHERE survey_year = ?", (year,))


def save_uploaded_year_data(
    df: pd.DataFrame,
    year: int,
    db_path: str | Path,
    file_name: str,
    content: bytes,
) -> None:
    """Save cleaned rows and the original CSV together for one survey year."""
    uploaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        with conn:
            _replace_response_rows(conn, df, year)
            _ensure_file_table(conn)
            conn.execute(
                f"INSERT INTO {_FILES_TABLE} "
                "(survey_year, file_name, uploaded_at, file_size, content) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(survey_year) DO UPDATE SET "
                "file_name=excluded.file_name, uploaded_at=excluded.uploaded_at, "
                "file_size=excluded.file_size, content=excluded.content",
                (year, file_name, uploaded_at, len(content), content),
            )


def list_survey_files(db_path: str | Path) -> list[SurveyFile]:
    """List one file-library row per stored year, including older data-only years."""
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn, _RESPONSES_TABLE):
            return []
        if _table_exists(conn, _FILES_TABLE):
            rows = conn.execute(
                f"SELECT r.survey_year, COUNT(*) AS response_count, "
                "f.file_name, f.uploaded_at, f.file_size "
                f"FROM {_RESPONSES_TABLE} AS r "
                f"LEFT JOIN {_FILES_TABLE} AS f ON f.survey_year = r.survey_year "
                "GROUP BY r.survey_year ORDER BY r.survey_year DESC"
            ).fetchall()
        else:
            rows = [
                (year, count, None, None, None)
                for year, count in conn.execute(
                    f"SELECT survey_year, COUNT(*) FROM {_RESPONSES_TABLE} "
                    "GROUP BY survey_year ORDER BY survey_year DESC"
                )
            ]
    return [
        SurveyFile(
            year=int(year),
            file_name=file_name or f"Survey {year} data",
            uploaded_at=uploaded_at,
            file_size=file_size,
            response_count=int(count),
            has_original=file_name is not None,
        )
        for year, count, file_name, uploaded_at, file_size in rows
    ]


def load_original_file(db_path: str | Path, year: int) -> tuple[str, bytes] | None:
    """Return the unchanged CSV bytes and filename, if this year has an original."""
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn, _FILES_TABLE):
            return None
        row = conn.execute(
            f"SELECT file_name, content FROM {_FILES_TABLE} WHERE survey_year = ?", (year,)
        ).fetchone()
    return (row[0], row[1]) if row else None


def delete_year_data(db_path: str | Path, year: int) -> None:
    """Delete one year's cleaned responses and original CSV in one transaction."""
    with sqlite3.connect(db_path) as conn:
        with conn:
            if _table_exists(conn, _RESPONSES_TABLE):
                conn.execute(f"DELETE FROM {_RESPONSES_TABLE} WHERE survey_year = ?", (year,))
            if _table_exists(conn, _FILES_TABLE):
                conn.execute(f"DELETE FROM {_FILES_TABLE} WHERE survey_year = ?", (year,))


def load_all_years(db_path: str | Path) -> pd.DataFrame:
    """Load every stored survey year, or an empty DataFrame when none exist."""
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn, _RESPONSES_TABLE):
            return pd.DataFrame()
        return pd.read_sql(f"SELECT * FROM {_RESPONSES_TABLE}", conn)


def load_year(db_path: str | Path, year: int) -> pd.DataFrame:
    """Load a single survey year's cleaned rows."""
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn, _RESPONSES_TABLE):
            return pd.DataFrame()
        return pd.read_sql(
            f"SELECT * FROM {_RESPONSES_TABLE} WHERE survey_year = ?", conn, params=(year,)
        )
