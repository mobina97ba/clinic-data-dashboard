"""Small ELT pipeline: load raw text -> SQL staging -> fact table -> marts -> quality checks.

Uses SQLite from the Python standard library, so it needs no install and no server.
The SQL lives in /sql and is deliberately plain so it ports to BigQuery/Dataform with small changes
(e.g. GLOB -> REGEXP_CONTAINS, SUBSTR date handling -> SAFE.PARSE_DATE).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .cleaning import MissingColumnsError, normalise_columns
from .config import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, STATUS_GROUPS

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
RAW_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


def load_raw(conn: sqlite3.Connection, raw: pd.DataFrame) -> int:
    """Extract/load step: store every value as untouched text, plus its row number in the file."""
    df = normalise_columns(raw).reset_index(drop=True)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise MissingColumnsError(missing, list(df.columns))
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[RAW_COLUMNS].astype("string")
    rows = [(i + 2, *[None if pd.isna(v) else str(v) for v in rec])  # +2: header is row 1
            for i, rec in enumerate(df.itertuples(index=False, name=None))]
    conn.execute("DROP TABLE IF EXISTS raw_appointments")
    conn.execute("CREATE TABLE raw_appointments (source_row INTEGER, "
                 + ", ".join(f"{c} TEXT" for c in RAW_COLUMNS) + ")")
    conn.executemany(f"INSERT INTO raw_appointments VALUES ({', '.join('?' * (len(RAW_COLUMNS) + 1))})", rows)

    # Reference table built from config.py so Python and SQL share one status definition.
    conn.execute("DROP TABLE IF EXISTS ref_status_groups")
    conn.execute("CREATE TABLE ref_status_groups (status TEXT PRIMARY KEY, status_group TEXT)")
    conn.executemany("INSERT INTO ref_status_groups VALUES (?, ?)",
                     [(s, g) for g, values in STATUS_GROUPS.items() for s in sorted(values)])
    return len(rows)


def run_models(conn: sqlite3.Connection) -> list[str]:
    """Run sql/*.sql in filename order."""
    ran = []
    for path in sorted(SQL_DIR.glob("*.sql")):
        conn.executescript(path.read_text())
        ran.append(path.name)
    conn.commit()
    return ran


def run_checks(conn: sqlite3.Connection) -> list[dict]:
    """Each check is a query that returns the offending rows. Zero rows = pass."""
    results = []
    for path in sorted((SQL_DIR / "checks").glob("*.sql")):
        bad = conn.execute(path.read_text()).fetchall()
        results.append({"check": path.stem, "passed": not bad, "failing_rows": len(bad)})
    return results


def build_warehouse(raw: pd.DataFrame, db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    load_raw(conn, raw)
    run_models(conn)
    return conn


def read_table(conn: sqlite3.Connection, name: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {name}", conn)
