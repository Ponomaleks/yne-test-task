---
id: T9
title: "Build the PowerOffice client with token, lookups and creates"
layer: "infra"
deps: []
blocks: ["T10"]
acs: ["AC-02", "AC-03", "AC-13"]
files_hint: ["app/clients/poweroffice.py", "tests/clients/test_poweroffice.py"]
owner: "Oleksandr Ponomarenko"
estimate: "M"
context_budget: "M"
status: "done"
step: "COMMIT"
---

# T9 — Build the PowerOffice client with token, lookups and creates

## Place in the sequence

- **Blocked by:** — · **Blocks:** T10 — Process one event · **Wave:** 1.
- **Lane:** own lane.

## Why (user story)

> **As a** Finance reviewer
> **I want** the order attached to the existing customer with the same orgnr, or to a new customer only when none exists
> **So that** customers are never created twice and invoices reach the right company
>
> — `spec.md §4, US-02, verbatim` · full text: [spec.md](../spec.md)

This task provides the lookups and creates the processor uses for lookup-before-create.

## Inlined context

> Outbound authentication — Accounting system: client-credentials token, fetched once and fetched again after an authentication rejection (spec §1, §3).
> Idempotency — Lookup before create: customer by normalized orgnr, order by external key `hubspot-deal-<dealId>` with exact equality.
> Pagination — No paging fields in the evidence for the PowerOffice customer and order searches, so one page is assumed.
>
> — `sad.md §8, abridged` · full text: [sad.md](../sad.md)

> A POST that fails with 5xx, a timeout or a network error is never retried by the client; the error goes back to the processor, which looks up by the external key before any new create.
>
> — `docs/architecture-map.md, clients row, abridged` · full text: [architecture-map.md](../../../architecture-map.md)

Endpoints:
- `POST /oauth/token`, Basic `client_id:client_secret`, form `grant_type=client_credentials` → `access_token`, `token_type` "Bearer", `expires_in` 900
- `GET /v2/Customers?organizationNumber={orgnr}` → top-level array; item `id` (number), `organizationNumber` (string)
- `GET /v2/SalesOrders?reference={key}` → top-level array, no paging fields
- `POST /v2/Customers` body `name`, `organizationNumber`, `emailAddress`, `countryCode` → customer with `id`
- `POST /v2/SalesOrders` body from T6 (`customerId`, `reference`, `currencyCode`, `lines[]`) — JSON, `Content-Type: application/json`
- Errors: `{"error", "message", "details", "traceId"}` — map to an error type only, never log the body

— `evidence/api-poweroffice.md` (token, searches) + `docs/interview-reference/task/yne-api-uk.md §PowerOffice` (creates, errors), abridged.

> **Hard rule:** Discount precision and the accounting-system error format are not verified (spec §1) — the error body is mapped to an error type only, never logged in full.
>
> — `sad.md §11, risk row 7, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient → read the evidence and task doc named above. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface. Outbound PowerOffice calls as listed above.

## Acceptance criteria

### AC-02 — happy

> **Given** a won deal whose company has a valid orgnr that matches no existing customer
> **When** the integration processes the event
> **Then** a new customer is created with the company's name, orgnr, invoice email and country, and the Draft sales order is attached to that new customer
>
> — `spec.md §5, AC-02, verbatim` · full text: [spec.md](../spec.md)

### AC-03 — cross-context

> **Given** a customer already exists for a company's orgnr, created earlier for another deal
> **When** a second won deal for the same company is processed
> **Then** the order is attached to the existing customer and no new customer is created
>
> — `spec.md §5, AC-03, verbatim` · full text: [spec.md](../spec.md)

### AC-13 — error

> **Given** the accounting system fails or does not answer while an order is being created
> **When** the integration handles that failure
> **Then** the unit of work is recorded as failed with the reason and stays persisted, and a retry first checks for an existing order with the deal's external key and creates one only if none is found
>
> — `spec.md §5, AC-13, verbatim` · full text: [spec.md](../spec.md)

This task owns the calls and the "POST never retried on 5xx/timeout" rule; T10 owns the decision flow.

## Checklist

- [ ] `PowerOfficeClient(base_url, client_id, client_secret, http: httpx.Client)`; 15 s timeout; token fetched lazily, fetched again once on 401 — `app/clients/poweroffice.py`
- [ ] `find_customers(orgnr) -> list`, `find_orders(reference) -> list` filtered to exact `reference ==` equality (spec §8 default) — `app/clients/poweroffice.py`
- [ ] `create_customer(name, orgnr, email, country_code) -> id`, `create_order(payload) -> id`; `Decimal` serialized without float loss — `app/clients/poweroffice.py`
- [ ] Retry 429 on any method and GET on 5xx/timeout; POST 5xx/timeout raises `AccountingError` subtype — `app/clients/poweroffice.py`
- [ ] MockTransport tests: 401 → one token refresh then success; POST 500 → raises, called once; order search returns a partial match → filtered out — `tests/clients/test_poweroffice.py` (create empty `tests/clients/__init__.py` if missing)

## Edge cases

| Case | Behaviour |
|---|---|
| Second 401 after a fresh token | raise an auth error (blocking) |
| Order search returns `hubspot-deal-1` and `hubspot-deal-10` for key `hubspot-deal-1` | only the exact match counts |
| Country `Norway` from the CRM | sent as `countryCode` `NO` (only Norway reaches create; foreign is held in T7) |
| POST times out | raises; never retried here |

## Definition of Done

- [ ] MockTransport tests above pass; no real network
- [ ] No token, secret or personal value in any log line
- [ ] `ruff check . && pytest` green
