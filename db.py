import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("STAFF_MVP_DB", "staff_mvp.db")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connect(db_path: str | None = None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def run_migration(db_path: str | None = None) -> None:
    migration_file = os.path.join(os.path.dirname(__file__), "migrations", "001_init.sql")
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    with connect(db_path) as conn:
        conn.executescript(sql)
