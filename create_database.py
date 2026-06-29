"""
create_database.py
──────────────────
Initialises the PlaceMux SQLite database and applies the full schema.
Run once before any other script.
"""

import sqlite3
import pathlib
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

DB_PATH  = pathlib.Path(__file__).parent / "database" / "placemux.db"
SQL_PATH = pathlib.Path(__file__).parent / "sql" / "create_tables.sql"


def create_database() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    log.info("Opening database at %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    ddl = SQL_PATH.read_text()
    conn.executescript(ddl)
    conn.commit()

    log.info("Schema created / verified ✓")
    return conn


def get_connection() -> sqlite3.Connection:
    """Return a connection to the existing database (used by other modules)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    create_database()
    log.info("Database ready.")
