import httpx

from app.clients.hubspot import HubSpotClient


def replay(hubspot: HubSpotClient, http: httpx.Client, target_url: str) -> dict[str, int]:
    """Post every recorded delivery, in order, unchanged, to the local endpoint."""
    counts = {"posted": 0, "acknowledged": 0, "rejected": 0}
    for delivery in hubspot.get_recorded_deliveries():
        # Raw bytes, never re-serialized: the signature covers the exact body.
        response = http.post(
            target_url,
            content=(delivery.body or "").encode("utf-8"),
            headers={k: str(v) for k, v in delivery.headers.items()},
        )
        counts["posted"] += 1
        if response.status_code == 204:
            counts["acknowledged"] += 1
        elif response.status_code == 401:
            counts["rejected"] += 1
    return counts
