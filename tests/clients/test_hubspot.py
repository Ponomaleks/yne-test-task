import httpx
import pytest

from app.clients.hubspot import DealNotFound, HubSpotClient, HubSpotError

DEAL = {
    "id": "101",
    "properties": {"amount": "100.00", "dealstage": "won", "pipeline": "default"},
    "associations": {
        "companies": {"results": [{"id": "7"}]},
        "line_items": {"results": [{"id": "11"}, {"id": "12"}]},
    },
}


def make_client(handler):
    sleeps = []
    client = HubSpotClient(
        "https://hs.test",
        "synthetic-token",
        httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleeps.append,
    )
    return client, sleeps


def test_get_deal_parses_associations_and_sends_bearer():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=DEAL)

    client, _ = make_client(handler)
    deal = client.get_deal("101")
    assert deal.id == "101"
    assert deal.company_ids == ["7"]
    assert deal.line_item_ids == ["11", "12"]
    assert seen[0].headers["Authorization"] == "Bearer synthetic-token"
    assert seen[0].extensions["timeout"]["read"] == 15


def test_deal_without_associations_has_empty_lists():
    client, _ = make_client(lambda r: httpx.Response(200, json={"id": "1", "properties": {}}))
    deal = client.get_deal("1")
    assert deal.company_ids == []
    assert deal.line_item_ids == []


def test_429_waits_retry_after_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json=DEAL)

    client, sleeps = make_client(handler)
    assert client.get_deal("101").id == "101"
    assert len(calls) == 2
    assert 3.0 in sleeps


def test_429_waits_ratelimit_interval_header():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(
                429, headers={"X-HubSpot-RateLimit-Interval-Milliseconds": "2000"}
            )
        return httpx.Response(200, json=DEAL)

    client, sleeps = make_client(handler)
    client.get_deal("101")
    assert 2.0 in sleeps


def test_429_without_headers_waits_default_10s_and_keeps_retrying():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) <= 3:
            return httpx.Response(429)
        return httpx.Response(200, json=DEAL)

    client, sleeps = make_client(handler)
    client.get_deal("101")
    assert len(calls) == 4
    assert sleeps.count(10.0) == 3


def test_404_raises_deal_not_found():
    client, _ = make_client(lambda r: httpx.Response(404, json={"message": "nope"}))
    with pytest.raises(DealNotFound):
        client.get_deal("999")


def test_5xx_get_retries_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=DEAL)

    client, _ = make_client(handler)
    assert client.get_deal("101").id == "101"
    assert len(calls) == 3


def test_5xx_exhausts_bounded_retries_and_raises():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(500)

    client, _ = make_client(handler)
    with pytest.raises(HubSpotError):
        client.get_deal("101")
    assert len(calls) == 3


def test_timeout_exhausts_retries_and_raises():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("stalled", request=request)

    client, _ = make_client(handler)
    with pytest.raises(HubSpotError):
        client.get_deal("101")
    assert len(calls) == 3


def test_invalid_response_raises_hubspot_error():
    client, _ = make_client(lambda r: httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(HubSpotError):
        client.get_deal("101")


def test_get_company_line_item_pipelines_and_deliveries():
    def handler(request):
        path = request.url.path
        if path.startswith("/crm/v3/objects/companies/"):
            return httpx.Response(
                200,
                json={"id": "7", "properties": {"name": "Acme", "orgnr": "123", "country": "SE",
                                                "fakturaepost": None}},
            )
        if path.startswith("/crm/v3/objects/line_items/"):
            return httpx.Response(
                200,
                json={"id": "11", "properties": {"name": "Item", "price": "10", "quantity": "2",
                                                 "discount": None}},
            )
        if path == "/crm/v3/pipelines/deals":
            return httpx.Response(
                200,
                json={"results": [{"id": "p", "stages": [{"id": "won", "metadata": {}}]}]},
            )
        if path == "/_testverktoy/webhooks":
            return httpx.Response(
                200,
                json={"results": [{"leveranse": 1, "method": "POST", "uri": "/x",
                                   "headers": {}, "body": "{}"}]},
            )
        return httpx.Response(500)

    client, _ = make_client(handler)
    assert client.get_company("7").properties.orgnr == "123"
    assert client.get_line_item("11").properties.quantity == "2"
    assert client.get_pipelines()["results"][0]["stages"][0]["id"] == "won"
    assert client.get_recorded_deliveries()[0].leveranse == 1


def test_get_line_item_requests_its_properties_explicitly():
    seen = []

    def handler(request):
        seen.append(request.url.params.get("properties"))
        return httpx.Response(
            200,
            json={"id": "11", "properties": {"name": "Item", "price": "10", "quantity": "2",
                                             "discount": "1.50"}},
        )

    client, _ = make_client(handler)
    assert client.get_line_item("11").properties.discount == "1.50"
    assert seen == ["name,price,quantity,discount"]
