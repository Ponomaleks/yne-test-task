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

    payload = {"reference": "hubspot-deal-1", "lines": [{"unitPrice": Decimal("0.10")}]}
    assert make_client(handler).create_order(payload) == 55
    assert seen["ctype"].startswith("application/json")
    assert '"unitPrice": 0.10' in seen["body"] or '"unitPrice":0.10' in seen["body"]


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
