import base64
import hashlib
import hmac
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.store import init_store
from app.web import create_app

SECRET = "synthetic-secret"
URI = "https://example.test/webhooks/hubspot"
TIMESTAMP = "1700000000000"


def sign(body: bytes, uri: str = URI) -> str:
    text = b"POST" + uri.encode() + body + TIMESTAMP.encode()
    return base64.b64encode(hmac.new(SECRET.encode(), text, hashlib.sha256).digest()).decode()


def event(event_id: int = 1, **extra) -> dict:
    return {
        "eventId": event_id,
        "objectId": 42,
        "subscriptionType": "deal.propertyChange",
        "propertyName": "dealstage",
        "propertyValue": "closedwon",
        "sourceId": "secret-source",
        **extra,
    }


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "store.db"
    init_store(path)
    return path


@pytest.fixture
def calls():
    return []


@pytest.fixture
def client(store, calls):
    app = create_app(
        store_path=store,
        secret=SECRET,
        webhook_uri=URI,
        process=lambda delivery_id, events: calls.append((delivery_id, events)),
    )
    return TestClient(app)


def post(client, payload, signature=None, timestamp=TIMESTAMP):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    headers = {"X-HubSpot-Signature-v3": sign(body) if signature is None else signature}
    if timestamp is not None:
        headers["X-HubSpot-Request-Timestamp"] = timestamp
    return client.post("/webhooks/hubspot", content=body, headers=headers)


def rows(store, table):
    conn = sqlite3.connect(store)
    try:
        return conn.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        conn.close()


def test_valid_delivery_returns_204_persists_and_schedules_processing(client, store, calls):
    response = post(client, [event(1), event(2)])

    assert response.status_code == 204
    assert len(rows(store, "deliveries")) == 1
    assert len(rows(store, "events")) == 2
    assert len(calls) == 1
    assert [e["event_id"] for e in calls[0][1]] == [1, 2]


def test_stored_rows_never_contain_property_value_or_source_id(client, store):
    post(client, [event(1)])

    dump = repr(rows(store, "events")) + repr(rows(store, "deliveries"))
    assert "closedwon" not in dump
    assert "secret-source" not in dump


def test_missing_signature_returns_401_with_rejection_and_no_processing(client, store, calls):
    body = json.dumps([event()]).encode()
    response = client.post(
        "/webhooks/hubspot", content=body, headers={"X-HubSpot-Request-Timestamp": TIMESTAMP}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "delivery.signature_missing"
    assert len(rows(store, "rejections")) == 1
    assert rows(store, "events") == []
    assert calls == []


def test_mismatched_signature_returns_401_with_rejection(client, store, calls):
    response = post(client, [event()], signature="not-the-signature")

    assert response.status_code == 401
    assert response.json()["code"] == "delivery.signature_mismatch"
    assert len(rows(store, "rejections")) == 1
    assert rows(store, "deliveries") == []
    assert calls == []


def test_signature_over_local_url_is_a_mismatch(client, store):
    body = json.dumps([event()]).encode()
    response = post(client, body, signature=sign(body, "http://testserver/webhooks/hubspot"))

    assert response.status_code == 401
    assert len(rows(store, "rejections")) == 1


def test_non_array_body_returns_400_and_stores_nothing(client, store, calls):
    response = post(client, {"eventId": 1})

    assert response.status_code == 400
    assert response.json()["code"] == "delivery.invalid_body"
    assert rows(store, "deliveries") == []
    assert rows(store, "events") == []
    assert calls == []


def test_repeated_delivery_returns_204_twice_and_stores_one_event_row(client, store):
    assert post(client, [event(7)]).status_code == 204
    assert post(client, [event(7)]).status_code == 204

    assert len(rows(store, "events")) == 1


def test_event_without_event_id_is_skipped_and_others_are_stored(client, store):
    bad = event(3)
    del bad["eventId"]

    response = post(client, [bad, event(4)])

    assert response.status_code == 204
    assert len(rows(store, "events")) == 1


def test_empty_array_returns_204_with_zero_event_count(client, store):
    assert post(client, []).status_code == 204
    assert rows(store, "deliveries")[0][3] == 0


def test_unwritable_store_returns_500_and_no_processing(tmp_path, calls):
    app = create_app(
        store_path=tmp_path / "missing-dir" / "store.db",
        secret=SECRET,
        webhook_uri=URI,
        process=lambda delivery_id, events: calls.append(delivery_id),
    )

    response = post(TestClient(app), [event()])

    assert response.status_code == 500
    assert response.json()["code"] == "delivery.not_persisted"
    assert calls == []
