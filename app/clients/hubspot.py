"""HubSpot (CRM) client: pacing, 429 wait, bounded GET retries, typed responses.

Personal values (company name, email) are returned to the caller, never logged.
"""

import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

TIMEOUT_SECONDS = 15.0
PACING_SECONDS = 0.6
DEFAULT_429_WAIT_SECONDS = 10.0  # the published rate-limit window
MAX_GET_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.0


class HubSpotError(Exception):
    """A CRM call failed after retries, or the response had an unexpected shape."""


class DealNotFound(HubSpotError):
    """The CRM reports that the deal does not exist (AC-11)."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _Assoc(_Model):
    results: list[dict[str, Any]] = []


class _Associations(_Model):
    companies: _Assoc = _Assoc()
    line_items: _Assoc = _Assoc()


class Deal(_Model):
    id: str
    properties: dict[str, Any] = {}
    associations: _Associations = _Associations()

    @property
    def company_ids(self) -> list[str]:
        return [r["id"] for r in self.associations.companies.results]

    @property
    def line_item_ids(self) -> list[str]:
        return [r["id"] for r in self.associations.line_items.results]


class CompanyProperties(_Model):
    name: str | None = None
    orgnr: str | None = None
    country: str | None = None
    fakturaepost: str | None = None


class Company(_Model):
    id: str
    properties: CompanyProperties = CompanyProperties()


class LineItemProperties(_Model):
    name: str | None = None
    price: str | None = None
    quantity: str | None = None
    discount: str | None = None


class LineItem(_Model):
    id: str
    properties: LineItemProperties = LineItemProperties()


class RecordedDelivery(_Model):
    leveranse: int
    method: str | None = None
    uri: str | None = None
    headers: dict[str, Any] = {}
    body: str | None = None


class _Deliveries(_Model):
    results: list[RecordedDelivery]


class HubSpotClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        http: httpx.Client,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._http = http
        self._sleep = sleep
        self._last_call: float | None = None

    def get_deal(self, deal_id: str) -> Deal:
        data = self._get(
            f"/crm/v3/objects/deals/{deal_id}",
            params={
                "associations": "companies,line_items",
                "properties": "amount,dealstage,pipeline,deal_currency_code",
            },
            not_found=DealNotFound,
        )
        return self._parse(Deal, data)

    def get_company(self, company_id: str) -> Company:
        data = self._get(
            f"/crm/v3/objects/companies/{company_id}",
            params={"properties": "name,orgnr,country,fakturaepost"},
        )
        return self._parse(Company, data)

    def get_line_item(self, line_item_id: str) -> LineItem:
        data = self._get(f"/crm/v3/objects/line_items/{line_item_id}")
        return self._parse(LineItem, data)

    def get_pipelines(self) -> dict[str, Any]:
        return self._get("/crm/v3/pipelines/deals")

    def get_recorded_deliveries(self) -> list[RecordedDelivery]:
        data = self._get("/_testverktoy/webhooks")
        return self._parse(_Deliveries, data).results

    def _parse(self, model: type[BaseModel], data: Any) -> Any:
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            raise HubSpotError(
                f"unexpected CRM response shape for {model.__name__}"
            ) from exc

    def _pace(self) -> None:
        if self._last_call is not None:
            remaining = PACING_SECONDS - (time.monotonic() - self._last_call)
            if remaining > 0:
                self._sleep(remaining)
        self._last_call = time.monotonic()

    @staticmethod
    def _rate_limit_wait(response: httpx.Response) -> float:
        retry_after = response.headers.get("Retry-After")
        interval = response.headers.get("X-HubSpot-RateLimit-Interval-Milliseconds")
        try:
            if retry_after is not None:
                return float(retry_after)
            if interval is not None:
                return float(interval) / 1000
        except ValueError:
            pass
        return DEFAULT_429_WAIT_SECONDS

    def _get(
        self,
        path: str,
        params: dict[str, str] | None = None,
        not_found: type[HubSpotError] = HubSpotError,
    ) -> Any:
        url = self._base_url + path
        failures = 0
        while True:
            self._pace()
            try:
                response = self._http.get(
                    url, params=params, headers=self._headers, timeout=TIMEOUT_SECONDS
                )
            except httpx.TransportError as exc:  # timeouts and network errors
                failures += 1
                if failures >= MAX_GET_ATTEMPTS:
                    raise HubSpotError(
                        f"CRM unreachable: {type(exc).__name__}"
                    ) from exc
                self._sleep(RETRY_BACKOFF_SECONDS)
                continue

            if response.status_code == 429:
                # The limit alone never fails the call: wait the window, retry.
                self._sleep(self._rate_limit_wait(response))
                continue
            if response.status_code == 404:
                raise not_found(f"CRM returned 404 for {path}")
            if response.status_code >= 500:
                failures += 1
                if failures >= MAX_GET_ATTEMPTS:
                    raise HubSpotError(
                        f"CRM returned {response.status_code} for {path}"
                    )
                self._sleep(RETRY_BACKOFF_SECONDS)
                continue
            if response.status_code >= 400:
                raise HubSpotError(f"CRM returned {response.status_code} for {path}")
            try:
                return response.json()
            except ValueError as exc:
                raise HubSpotError(f"CRM returned non-JSON for {path}") from exc
