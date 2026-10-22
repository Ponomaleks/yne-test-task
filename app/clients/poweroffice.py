"""PowerOffice (accounting system) HTTP client.

Retry policy: 429 on any method (honoring Retry-After); GET on 5xx/timeout/network
error. A POST is never retried on 5xx/timeout: the processor looks up by the
external key before any new create. Error bodies are never logged or put into
exception messages.
"""

import json
import re
import time
from decimal import Decimal

import httpx

TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 3
_DECIMAL_MARK = "__decimal__:"


class AccountingError(Exception):
    """Accounting system failed or did not answer."""


class AccountingAuthError(AccountingError):
    """Authentication rejected even with a fresh token (blocking)."""


def _mark_decimals(value):
    if isinstance(value, Decimal):
        return f"{_DECIMAL_MARK}{value}"
    if isinstance(value, dict):
        return {k: _mark_decimals(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_mark_decimals(v) for v in value]
    return value


def dumps_exact(payload) -> str:
    """JSON-encode with Decimal written as a plain number, without float loss."""
    text = json.dumps(_mark_decimals(payload))
    return re.sub(rf'"{_DECIMAL_MARK}([^"]+)"', r"\1", text)


class PowerOfficeClient:
    def __init__(self, base_url, client_id, client_secret, http: httpx.Client):
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http
        self._token = None

    # --- public API ---

    def find_customers(self, orgnr) -> list:
        return self._request("GET", "/v2/Customers", params={"organizationNumber": orgnr}).json()

    def find_orders(self, reference) -> list:
        found = self._request("GET", "/v2/SalesOrders", params={"reference": reference}).json()
        # The search may match partially (deal-1 vs deal-10): keep exact equality only.
        return [order for order in found if order.get("reference") == reference]

    def create_customer(self, name, orgnr, email, country_code):
        body = {
            "name": name,
            "organizationNumber": orgnr,
            "emailAddress": email,
            "countryCode": country_code,
        }
        return self._post("/v2/Customers", body)

    def create_order(self, payload):
        return self._post("/v2/SalesOrders", payload)

    # --- internals ---

    def _post(self, path, body):
        response = self._request(
            "POST",
            path,
            content=dumps_exact(body),
            headers={"Content-Type": "application/json"},
        )
        return response.json()["id"]

    def _fetch_token(self):
        try:
            response = self._http.post(
                f"{self._base_url}/oauth/token",
                auth=(self._client_id, self._client_secret),
                data={"grant_type": "client_credentials"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise AccountingError(f"token request failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise AccountingAuthError(f"token request rejected: {response.status_code}")
        self._token = response.json()["access_token"]

    def _send(self, method, path, **kwargs):
        if self._token is None:
            self._fetch_token()
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {self._token}"}
        return self._http.request(
            method, f"{self._base_url}{path}", headers=headers, timeout=TIMEOUT_SECONDS, **kwargs
        )

    def _request(self, method, path, **kwargs):
        refreshed = False
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._send(method, path, **kwargs)
            except httpx.HTTPError as exc:
                if method == "GET" and attempt < MAX_ATTEMPTS:
                    continue
                raise AccountingError(f"{method} {path} failed: {type(exc).__name__}") from exc

            status = response.status_code
            if status == 401:
                if refreshed:
                    raise AccountingAuthError(f"{method} {path} rejected after token refresh")
                refreshed = True
                self._fetch_token()
                continue
            if status == 429 and attempt < MAX_ATTEMPTS:
                time.sleep(_retry_after(response))
                continue
            if status >= 500 and method == "GET" and attempt < MAX_ATTEMPTS:
                continue
            if status >= 400:
                raise AccountingError(f"{method} {path} returned {status}")
            return response


def _retry_after(response) -> float:
    try:
        return min(float(response.headers.get("Retry-After", 1)), 30.0)
    except ValueError:
        return 1.0
