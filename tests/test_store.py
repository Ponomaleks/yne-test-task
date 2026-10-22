import sqlite3

import pytest

from app.store import (
    has_final_outcome,
    init_store,
    last_outcome,
    last_outcomes,
    record_outcome,
    save_delivery,
    save_events,
    save_rejection,
)


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


def _event(
    event_id=1, deal_id=111, subscription_type="deal.propertyChange", property_name="dealstage"
):
    return {
        "event_id": event_id,
        "deal_id": deal_id,
        "subscription_type": subscription_type,
        "property_name": property_name,
    }


def _store(tmp_path):
    db_path = tmp_path / "store.sqlite3"
    init_store(db_path)
    return db_path


def _rows(db_path, sql):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_save_delivery_returns_increasing_ids(tmp_path):
    db_path = _store(tmp_path)

    first = save_delivery(db_path, 1700000000000, "a" * 64, 2)
    second = save_delivery(db_path, 1700000000001, "b" * 64, 0)

    assert second > first
    assert _rows(db_path, "SELECT event_count FROM deliveries ORDER BY id") == [(2,), (0,)]


def test_save_events_twice_keeps_one_row_and_first_received_at(tmp_path):
    db_path = _store(tmp_path)

    save_events(db_path, [_event(1, 111)])
    first = _rows(db_path, "SELECT received_at FROM events")
    save_events(db_path, [_event(1, 111), _event(2, 222, property_name=None)])

    assert _rows(db_path, "SELECT event_id, deal_id FROM events ORDER BY event_id") == [
        (1, "111"),
        (2, "222"),
    ]
    assert _rows(db_path, "SELECT received_at FROM events WHERE event_id = 1") == first


def test_save_rejection_stores_technical_identity_only(tmp_path):
    db_path = _store(tmp_path)

    save_rejection(db_path, None, "c" * 64, "signature missing")
    save_rejection(db_path, "1700000000000", "d" * 64, "signature mismatch")

    assert _rows(db_path, "SELECT request_timestamp, reason FROM rejections ORDER BY id") == [
        (None, "signature missing"),
        ("1700000000000", "signature mismatch"),
    ]


def test_last_outcome_is_none_without_outcome(tmp_path):
    db_path = _store(tmp_path)
    save_events(db_path, [_event(1)])

    assert last_outcome(db_path, 1) is None
    assert has_final_outcome(db_path, 1) is False


def test_last_outcome_returns_latest_row(tmp_path):
    db_path = _store(tmp_path)
    save_events(db_path, [_event(1)])
    record_outcome(db_path, 1, 111, "failed", "timeout", False)
    record_outcome(db_path, 1, 111, "ordered", "created", False)

    row = last_outcome(db_path, 1)

    assert row["outcome"] == "ordered"
    assert row["reason"] == "created"
    assert row["dry_run"] == 0


@pytest.mark.parametrize("outcome", ["ordered", "skipped", "held"])
def test_final_outcomes_are_final(tmp_path, outcome):
    db_path = _store(tmp_path)
    save_events(db_path, [_event(1)])
    record_outcome(db_path, 1, 111, outcome, "r", False)

    assert has_final_outcome(db_path, 1) is True


def test_failed_outcome_is_not_final(tmp_path):
    db_path = _store(tmp_path)
    save_events(db_path, [_event(1)])
    record_outcome(db_path, 1, 111, "failed", "r", False)

    assert has_final_outcome(db_path, 1) is False


def test_dry_run_outcome_is_not_final(tmp_path):
    db_path = _store(tmp_path)
    save_events(db_path, [_event(1)])
    record_outcome(db_path, 1, 111, "ordered", "r", True)

    assert has_final_outcome(db_path, 1) is False


def test_outcome_for_unknown_event_violates_foreign_key(tmp_path):
    db_path = _store(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        record_outcome(db_path, 99, 111, "failed", "r", False)


def test_last_outcomes_has_one_row_per_event_ordered_by_event_id(tmp_path):
    db_path = _store(tmp_path)
    save_events(db_path, [_event(2, 222), _event(1, 111), _event(3, 333)])
    record_outcome(db_path, 2, 222, "failed", "r", False)
    record_outcome(db_path, 2, 222, "skipped", "later", False)
    record_outcome(db_path, 1, 111, "ordered", "r", False)

    rows = last_outcomes(db_path)

    assert [(r["event_id"], r["outcome"]) for r in rows] == [(1, "ordered"), (2, "skipped")]


def test_init_store_creates_a_missing_parent_folder(tmp_path):
    db_path = tmp_path / "data" / "store.db"

    init_store(db_path)

    assert db_path.is_file()
