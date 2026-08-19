"""Create the MySQL database (if needed) and apply sql/schema.sql.

Usage:
    python scripts/setup_database.py
"""

import sys
from pathlib import Path

# Allow running as `python scripts/setup_database.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymysql
from pymysql.constants import CLIENT

from src.config import DB_CONFIG

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def run_schema() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    sql_text = SCHEMA_PATH.read_text()

    # No default database selected — schema.sql itself issues CREATE DATABASE / USE.
    # Executed as a single multi-statement batch (CLIENT.MULTI_STATEMENTS) rather
    # than splitting on ';' in Python, since that breaks on any ';' inside a
    # string literal (e.g. a COMMENT).
    conn = pymysql.connect(
        host=DB_CONFIG.host,
        port=DB_CONFIG.port,
        user=DB_CONFIG.user,
        password=DB_CONFIG.password,
        charset="utf8mb4",
        client_flag=CLIENT.MULTI_STATEMENTS,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_text)
            while cursor.nextset():
                pass
        conn.commit()
    finally:
        conn.close()

    print(f"Schema applied successfully to database '{DB_CONFIG.database}' "
          f"at {DB_CONFIG.host}:{DB_CONFIG.port}.")


if __name__ == "__main__":
    run_schema()
