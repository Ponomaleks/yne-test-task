import json
from decimal import Decimal

import httpx
import pytest

from app.clients.poweroffice import (
    AccountingAuthError,
    AccountingError,
    PowerOfficeClient,
)

BASE = "https://po.example.test"


def make_client(handler):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return PowerOfficeClient(BASE, "placeholder-id", "placeholder-secret", http)


def token_response():
    return httpx.Response(
        200,
        json={"access_token": "tok", "token_type": "Bearer", "expires_in": 900},
    )


def test_401_triggers_one_token_refresh_then_succeeds():
    calls = {"token": 0, "get": 0}

    def handler(request):
        if request.url.path == "/oauth/token":
            calls["token"] += 1
            return token_response()
        calls["get"] += 1
        if calls["get"] == 1:
            return httpx.Response(401, json={"error": "x"})
        return httpx.Response(200, json=[{"id": 7, "organizationNumber": "123456789"}])

    client = make_client(handler)
    assert client.find_customers("123456789") == [
        {"id": 7, "organizationNumber": "123456789"}
    ]
    assert calls == {"token": 2, "get": 2}


def test_second_401_raises_auth_error():
    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        return httpx.Response(401, json={})

    with pytest.raises(AccountingAuthError):
        make_client(handler).find_customers("123456789")


def test_post_500_raises_and_is_not_retried():
    posts = []

    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        posts.append(request)
        return httpx.Response(500, json={"error": "boom", "message": "secret-ish"})

    with pytest.raises(AccountingError) as exc:
        make_client(handler).create_order({"reference": "hubspot-deal-1"})
    assert "secret-ish" not in str(exc.value)
    assert len(posts) == 1


# Synthetic body shaped like the documented error: {"error", "message", "details", "traceId"}.
# Only `details[].field` is read; the shape of a details item is otherwise not verified.
VALIDATION_ERROR_BODY = {
    "error": "ValidationError",
    "message": "synthetic-message-text",
    "details": [{"field": "Lines[0].UnitPriceExVat"}, {"field": "customerId"}],
    "traceId": "synthetic-trace-id",
}


def test_post_400_logs_status_error_and_field_names_only(caplog):
    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        return httpx.Response(400, json=VALIDATION_ERROR_BODY)

    with caplog.at_level("INFO"), pytest.raises(AccountingError) as exc:
        make_client(handler).create_order({"reference": "hubspot-deal-1"})

    assert exc.value.status == 400
    assert exc.value.error_code == "ValidationError"
    assert exc.value.fields == ["Lines[0].UnitPriceExVat", "customerId"]
    logged = "status=400 error=ValidationError fields=Lines[0].UnitPriceExVat,customerId"
    assert logged in caplog.text
    assert "POST /v2/SalesOrders" in caplog.text
    assert "synthetic-message-text" not in caplog.text
    assert "synthetic-trace-id" not in caplog.text
    assert "synthetic-message-text" not in str(exc.value)


def test_error_without_documented_body_logs_status_only(caplog):
    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        return httpx.Response(400, text="not json")

    with caplog.at_level("INFO"), pytest.raises(AccountingError) as exc:
        make_client(handler).create_order({"reference": "hubspot-deal-1"})

    assert (exc.value.status, exc.value.error_code, exc.value.fields) == (400, "unknown", [])
    assert "status=400 error=unknown fields=" in caplog.text


def test_error_code_that_is_not_a_plain_token_is_not_logged(caplog):
    body = {"error": "value with spaces a@b.test", "details": [{"field": "x y"}, "bad"]}

    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        return httpx.Response(400, json=body)

    with caplog.at_level("INFO"), pytest.raises(AccountingError) as exc:
        make_client(handler).create_order({"reference": "hubspot-deal-1"})

    assert (exc.value.error_code, exc.value.fields) == ("unknown", [])
    assert "a@b.test" not in caplog.text


def test_post_timeout_raises_and_is_not_retried():
    posts = []

    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        posts.append(request)
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(AccountingError):
        make_client(handler).create_customer("Acme", "123456789", "a@b.test", "NO")
    assert len(posts) == 1


def test_get_5xx_is_retried():
    gets = []

    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        gets.append(request)
        if len(gets) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=[])

    assert make_client(handler).find_customers("123456789") == []
    assert len(gets) == 2


def test_order_search_keeps_only_exact_reference():
    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        assert request.url.params["reference"] == "hubspot-deal-1"
        return httpx.Response(
            200,
            json=[
                {"id": 1, "reference": "hubspot-deal-1"},
                {"id": 2, "reference": "hubspot-deal-10"},
            ],
        )

    found = make_client(handler).find_orders("hubspot-deal-1")
    assert [o["id"] for o in found] == [1]


def test_create_order_sends_decimal_exactly_and_returns_id():
    seen = {}

    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        seen["body"] = request.content.decode()
        seen["ctype"] = request.headers["content-type"]
        return httpx.Response(201, json={"id": 55})

    payload = {"reference": "hubspot-deal-1", "lines": [{"unitPriceExVat": Decimal("0.10")}]}
    assert make_client(handler).create_order(payload) == 55
    assert seen["ctype"].startswith("application/json")
    assert '"unitPriceExVat": 0.10' in seen["body"] or '"unitPriceExVat":0.10' in seen["body"]


def test_create_customer_body_and_id():
    seen = {}

    def handler(request):
        if request.url.path == "/oauth/token":
            return token_response()
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 9})

    cid = make_client(handler).create_customer("Acme", "123456789", "a@b.test", "NO")
    assert cid == 9
    assert seen["body"] == {
        "name": "Acme",
        "organizationNumber": "123456789",
        "emailAddress": "a@b.test",
        "countryCode": "NO",
    }
