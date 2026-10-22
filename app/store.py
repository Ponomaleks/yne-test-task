import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def init_store(path: str | Path) -> None:
    # A short-lived connection per operation: sqlite3 connections are bound to their thread.
    conn = sqlite3.connect(path)
    try:
        with conn:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    finally:
        conn.close()
