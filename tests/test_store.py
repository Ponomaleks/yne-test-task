import sqlite3

from app.store import init_store


def test_schema_applies_twice_to_a_fresh_file(tmp_path):
    db_path = tmp_path / "store.sqlite3"

    init_store(db_path)
    init_store(db_path)

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    finally:
        conn.close()
