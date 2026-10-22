---
id: T8
title: "Build the HubSpot client with pacing, 429 wait and GET retries"
layer: "infra"
deps: []
blocks: ["T10", "T13"]
acs: ["AC-11", "AC-14"]
files_hint: ["app/clients/hubspot.py", "tests/clients/test_hubspot.py"]
owner: "Oleksandr Ponomarenko"
estimate: "M"
context_budget: "M"
status: "done"
step: "COMMIT"
---

# T8 — Build the HubSpot client with pacing, 429 wait and GET retries

## Place in the sequence

- **Blocked by:** — · **Blocks:** T10 — Process one event, T13 — Replay module · **Wave:** 1.
- **Lane:** own lane.

## Why (user story)

> **As an** Integration operator
> **I want** repeated deliveries, repeated events and failures of the CRM or the accounting system to never create a second order or lose an event
> **So that** I can replay and retry without fear
>
> — `spec.md §4, US-04, verbatim` · full text: [spec.md](../spec.md)

This task makes CRM reads survive the rate limit and transient errors, and reports "deal not found" distinctly.

## Inlined context

> Timeouts, retries, rate limit — ≤ 15 s timeout on every call. CRM calls are paced 600 ms apart (evidence probe). On 429, honor `Retry-After` when present, else wait `X-HubSpot-RateLimit-Interval-Milliseconds`, then retry (AC-14; `Retry-After` not observed per FINDINGS).
> Outbound authentication — CRM: app token.
> Pagination — one page is assumed. Deal association paging is a spec §3 known limitation.
>
> — `sad.md §8, Timeouts/Outbound authentication/Pagination, abridged` · full text: [sad.md](../sad.md)

> clients: `httpx.Client`: timeout on every call. Automatic retries only for GET requests (429, 5xx, timeout, network error) and for 429 on any method.
>
> — `docs/architecture-map.md, clients row, abridged` · full text: [architecture-map.md](../../../architecture-map.md)

Endpoints (evidence, `Authorization: Bearer {HUBSPOT_APP_TOKEN}`):
- `GET /crm/v3/objects/deals/{id}?associations=companies,line_items&properties=amount,dealstage,pipeline,deal_currency_code` → `id` (string), `properties`, `associations.companies.results[].id`, `associations.line_items.results[].id`
- `GET /crm/v3/objects/companies/{id}?properties=name,orgnr,country,fakturaepost`
- `GET /crm/v3/objects/line_items/{id}` → `properties.name`, `price`, `quantity`, `discount` (strings or null)
- `GET /crm/v3/pipelines/deals` → `results[].stages[].metadata`
- `GET /_testverktoy/webhooks` → `results[]` with `leveranse`, `method`, `uri`, `headers`, `body` (string)

— `evidence/api-hubspot-deal.md`, `api-hubspot-deals-summary.md`, `api-hubspot-pipelines.md`, `api-hubspot-webhooks.md`, request lines + shapes, abridged. Line item property list beyond these and the 404 body are not in evidence: treat any `404` on the deal as "not found".

> **Hard rule:** pydantic models also validate CRM and accounting-system responses in `app/clients/`. Personal values (company name, email) are returned to the caller but never logged.
>
> — `sad.md §2 Technical + spec.md §6.1, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient → read the four evidence files and [sad.md](../sad.md) §8. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface. Outbound HubSpot calls as listed above.

## Acceptance criteria

### AC-11 — error

> **Given** an event names a deal that the CRM reports as not existing
> **When** the integration processes the event
> **Then** the unit of work is held for review with the reason "deal not found" and is not retried automatically
>
> — `spec.md §5, AC-11, verbatim` · full text: [spec.md](../spec.md)

### AC-14 — error

> **Given** the CRM reports that its request limit is reached
> **When** the integration is reading deals, companies or line items
> **Then** it waits for the limit window and continues, and no event is lost or marked failed because of the limit alone
>
> — `spec.md §5, AC-14, verbatim` · full text: [spec.md](../spec.md)

This task raises `DealNotFound` on 404 (T10 records the hold) and owns the 429 wait.

## Checklist

- [ ] `HubSpotClient(base_url, token, http: httpx.Client, sleep=time.sleep)`; 15 s timeout; injectable `sleep` so tests do not wait — `app/clients/hubspot.py`
- [ ] Pacing 600 ms between calls; 429 → wait `Retry-After` seconds or `X-HubSpot-RateLimit-Interval-Milliseconds`, retry; GET retry on 5xx/timeout/network with a small bounded count — `app/clients/hubspot.py`
- [ ] Methods `get_deal`, `get_company`, `get_line_item`, `get_pipelines`, `get_recorded_deliveries`; pydantic models for the fields above; `DealNotFound` on 404 — `app/clients/hubspot.py`
- [ ] Tests with `httpx.MockTransport` and synthetic fixtures: 429 then 200 succeeds and sleeps the interval; 404 → `DealNotFound`; 5xx exhausts retries → raises; stalled transport → timeout error — `tests/clients/test_hubspot.py` (create empty `tests/clients/__init__.py` if missing)

## Edge cases

| Case | Behaviour |
|---|---|
| 429 with no headers at all | wait a default of 10 000 ms (the published window), then retry |
| Repeated 429 | keeps waiting and retrying; never turns into a failed outcome by itself |
| Deal with no associations key | empty company and line item lists |
| Response fails pydantic validation | raises a clear error type (T10 records failed) |

## Definition of Done

- [ ] MockTransport tests above pass; no real network
- [ ] No token or personal value in any log line
- [ ] `ruff check . && pytest` green
