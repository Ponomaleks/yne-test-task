import sqlite3
import time
from contextlib import closing
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

FINAL_OUTCOMES = ("ordered", "skipped", "held")

_OUTCOME_COLUMNS = "id, event_id, deal_id, outcome, reason, dry_run, recorded_at"


def init_store(path: str | Path) -> None:
    # A short-lived connection per operation: sqlite3 connections are bound to their thread.
    conn = sqlite3.connect(path)
    try:
        with conn:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    finally:
        conn.close()


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def save_delivery(
    path: str | Path, request_timestamp: int, body_sha256: str, event_count: int
) -> int:
    with closing(_connect(path)) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO deliveries (request_timestamp, body_sha256, event_count, received_at)"
            " VALUES (?, ?, ?, ?)",
            (request_timestamp, body_sha256, event_count, _now_ms()),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("deliveries insert returned no row id")
        return cursor.lastrowid


def save_events(path: str | Path, events: list[dict]) -> None:
    now = _now_ms()
    rows = [
        (e["event_id"], str(e["deal_id"]), e["subscription_type"], e.get("property_name"), now)
        for e in events
    ]
    with closing(_connect(path)) as conn, conn:
        conn.executemany(
            "INSERT OR IGNORE INTO events"
            " (event_id, deal_id, subscription_type, property_name, received_at)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
        )


def save_rejection(
    path: str | Path, request_timestamp: str | None, body_sha256: str, reason: str
) -> None:
    with closing(_connect(path)) as conn, conn:
        conn.execute(
            "INSERT INTO rejections (request_timestamp, body_sha256, reason, received_at)"
            " VALUES (?, ?, ?, ?)",
            (request_timestamp, body_sha256, reason, _now_ms()),
        )


def record_outcome(
    path: str | Path, event_id: int, deal_id: int | str, outcome: str, reason: str, dry_run: bool
) -> None:
    with closing(_connect(path)) as conn, conn:
        conn.execute(
            "INSERT INTO outcomes (event_id, deal_id, outcome, reason, dry_run, recorded_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, str(deal_id), outcome, reason, int(dry_run), _now_ms()),
        )


def last_outcome(path: str | Path, event_id: int) -> dict | None:
    with closing(_connect(path)) as conn:
        row = conn.execute(
            f"SELECT {_OUTCOME_COLUMNS} FROM outcomes WHERE event_id = ? ORDER BY id DESC LIMIT 1",
            (event_id,),
        ).fetchone()
    return dict(row) if row else None


def has_final_outcome(path: str | Path, event_id: int) -> bool:
    row = last_outcome(path, event_id)
    return row is not None and row["outcome"] in FINAL_OUTCOMES and row["dry_run"] == 0


def last_outcomes(path: str | Path) -> list[dict]:
    with closing(_connect(path)) as conn:
        rows = conn.execute(
            f"SELECT {_OUTCOME_COLUMNS} FROM outcomes"
            " WHERE id IN (SELECT MAX(id) FROM outcomes GROUP BY event_id) ORDER BY event_id"
        ).fetchall()
    return [dict(row) for row in rows]
