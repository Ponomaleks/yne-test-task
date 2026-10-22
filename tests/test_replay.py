import httpx

from app.clients.hubspot import RecordedDelivery
from app.replay import replay

URL = "http://127.0.0.1:8000/webhooks/hubspot"


class FakeHubSpot:
    def __init__(self, deliveries):
        self._deliveries = deliveries

    def get_recorded_deliveries(self):
        return self._deliveries


def _delivery(n, body, sig):
    return RecordedDelivery(
        leveranse=n,
        method="POST",
        uri=URL,
        headers={
            "Content-Type": "application/json",
            "X-HubSpot-Signature-v3": sig,
            "X-HubSpot-Request-Timestamp": "1700000000000",
        },
        body=body,
    )


def _run(deliveries, statuses):
    seen = []
    codes = iter(statuses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(next(codes))

    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = replay(FakeHubSpot(deliveries), http, URL)
    return result, seen


def test_posts_in_order_with_original_headers_and_identical_bytes():
    first = '[{"objectId":  1,  "name":"Ærlig"}]'
    second = '[{"objectId":2}]'
    deliveries = [_delivery(1, first, "sig-a"), _delivery(2, second, "sig-b")]

    result, seen = _run(deliveries, [204, 204])

    assert [r.content for r in seen] == [first.encode("utf-8"), second.encode("utf-8")]
    assert [r.headers["X-HubSpot-Signature-v3"] for r in seen] == ["sig-a", "sig-b"]
    assert seen[0].headers["X-HubSpot-Request-Timestamp"] == "1700000000000"
    assert seen[0].headers["Content-Type"] == "application/json"
    assert all(str(r.url) == URL and r.method == "POST" for r in seen)
    assert result == {"posted": 2, "acknowledged": 2, "rejected": 0}


def test_401_counts_as_rejected():
    deliveries = [_delivery(1, "[]", "a"), _delivery(2, "[]", "b")]

    result, _ = _run(deliveries, [204, 401])

    assert result == {"posted": 2, "acknowledged": 1, "rejected": 1}
