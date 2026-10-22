import sqlite3

import pytest

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


def _fresh_conn(tmp_path):
    db_path = tmp_path / "store.sqlite3"
    init_store(db_path)
    return sqlite3.connect(db_path)


def test_schema_has_four_tables_and_outcomes_index(tmp_path):
    conn = _fresh_conn(tmp_path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master").fetchall()
        names = {row[0] for row in rows}
    finally:
        conn.close()

    assert {"deliveries", "events", "outcomes", "rejections", "idx_outcomes_event_id"} <= names


def test_same_event_id_inserted_twice_leaves_one_row(tmp_path):
    conn = _fresh_conn(tmp_path)
    try:
        for _ in range(2):
            conn.execute(
                "INSERT OR IGNORE INTO events (event_id, deal_id, subscription_type, received_at)"
                " VALUES (1, 'd1', 'deal.creation', 100)"
            )
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    finally:
        conn.close()


def test_outcome_outside_the_four_values_is_rejected(tmp_path):
    conn = _fresh_conn(tmp_path)
    try:
        conn.execute(
            "INSERT INTO events (event_id, deal_id, subscription_type, received_at)"
            " VALUES (1, 'd1', 'deal.creation', 100)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO outcomes (event_id, deal_id, outcome, reason, dry_run, recorded_at)"
                " VALUES (1, 'd1', 'unknown', 'x', 0, 100)"
            )
    finally:
        conn.close()
