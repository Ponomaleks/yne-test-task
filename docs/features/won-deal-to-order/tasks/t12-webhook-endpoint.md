---
id: T12
title: "Add the webhook endpoint: verify, persist, acknowledge, schedule"
layer: "ports"
deps: ["T2", "T3"]
blocks: ["T15"]
acs: ["AC-12", "AC-15"]
files_hint: ["app/web.py", "tests/test_web.py"]
owner: "Oleksandr Ponomarenko"
estimate: "M"
context_budget: "M"
status: "todo"
step: ""
---

# T12 — Add the webhook endpoint: verify, persist, acknowledge, schedule

## Place in the sequence

- **Blocked by:** T2 — store, T3 — signature · **Blocks:** T15 — Config and CLI wiring · **Wave:** 3.
- **Lane:** own lane. Processing is injected as a callable, so this task does not wait for T10/T11.

## Why (user story)

> **As an** Integration operator
> **I want** deliveries whose signature does not prove they came from the CRM to be rejected
> **So that** nobody can create orders by sending forged deliveries
>
> — `spec.md §4, US-05, verbatim` · full text: [spec.md](../spec.md)

This task is the only inbound surface: it rejects forged deliveries and acknowledges genuine ones before any processing.

## Inlined context

> builds the signed text over HUBSPOT_WEBHOOK_URI, compares in constant time → signature missing or not matching: records the rejection with the timestamp header and a SHA-256 of the body, rejects, no event is processed.
> signature valid: validates the body, a bad event is recorded and counted → persists the delivery and each new event by its event ID → acknowledges before any processing → background task.
>
> — `sad.md §6, Flow 4, abridged` · full text: [sad.md](../sad.md)

> Validation — An event that fails body validation is logged and counted in the delivery summary, not stored (without a usable event ID it has no key in the store); the others continue.
>
> — `sad.md §8, Validation, abridged` · full text: [sad.md](../sad.md)

> Sync endpoints; FastAPI `BackgroundTasks` runs the processing right after the response (ADR-0004).
>
> — `sad.md §2 Technical + ADR-0004 Option 1, abridged` · full text: [ADR-0004](../adr/0004-process-events-in-a-background-task-and-retry-by-replay.md)

Existing code: `app/web.py` `create_app()` takes no arguments and `tests/test_smoke.py` calls it that way —
keep a no-argument call working (e.g. keyword arguments with defaults); never edit the smoke test.

**Fallback:** insufficient → read [openapi.yaml](../contracts/openapi.yaml) and [sad.md](../sad.md) §6 Flow 4. Do not guess.

## Data delta

| Table | Change |
|---|---|
| `deliveries` | insert on valid signature |
| `events` | `INSERT OR IGNORE` per valid event |
| `rejections` | insert on missing/mismatched signature |

— `data-model.md §Entities, abridged` · full text: [data-model.md](../data-model.md)

## API contract

- `POST /webhooks/hubspot` → `204` (persisted, before processing) · errors: `401 delivery.signature_missing`, `401 delivery.signature_mismatch`, `400 delivery.invalid_body` (valid signature, body not a JSON array; nothing stored), `500 delivery.not_persisted` (store write failed; not acknowledged).
- Headers read: `X-HubSpot-Signature-v3`, `X-HubSpot-Request-Timestamp` (stored as INTEGER; missing or non-digits → mismatch, rejection stores it as text or NULL).
- Event fields stored: `eventId` → `event_id`, `objectId` → `deal_id` (text), `subscriptionType`, `propertyName` (nullable). Extra fields allowed and ignored; `propertyValue`, `sourceId` never stored.
- Error body: `{"code", "message"}`.

— `contracts/openapi.yaml, operationId receiveDelivery + schemas Error/Event, abridged` · full text: [openapi.yaml](../contracts/openapi.yaml)

## Acceptance criteria

### AC-15 — authorization

> **Given** a delivery whose signature is missing or does not match the delivery content
> **When** the integration receives it
> **Then** the delivery is rejected, none of its events are processed, and the rejection is recorded with the delivery's technical identity only
>
> — `spec.md §5, AC-15, verbatim` · full text: [spec.md](../spec.md)

### AC-12 — domain invariant

> **Given** an event that already has a final outcome (ordered, skipped or held for review), or a won event for a deal that already has its Draft sales order
> **When** that event arrives again, or the other won event is processed
> **Then** the event with a final outcome keeps that outcome as its only recorded outcome, and the run summary counts it as "duplicate event"; the won event for a deal with an order creates no second order and is recorded as skipped with the reason "order already exists", found by the deal's external key (AC-13), not by the event ID; an event whose last outcome is failed is not a duplicate and is processed again; an amount event for a deal that already has its order gets the reason "change after order, not handled" instead (AC-16)
>
> — `spec.md §5, AC-12, verbatim` · full text: [spec.md](../spec.md)

This task owns the endpoint half of AC-12: a repeated delivery gets the same `204` and stores no second event row.

## Checklist

- [ ] `create_app(*, store_path=None, secret=None, webhook_uri=None, process=None)`; route only registered when configured, so `create_app()` still boots — `app/web.py`
- [ ] Read the raw body (`await request.body()` or a sync dependency), verify with `is_valid_signature` before parsing — `app/web.py`
- [ ] Reject → `save_rejection` + 401 JSON; parse → 400 if not a list; per event pydantic validation, bad ones logged + counted — `app/web.py`
- [ ] `save_delivery` + `save_events`; store error → 500; else `background_tasks.add_task(process, delivery_id, events)`, return 204 — `app/web.py`
- [ ] `TestClient` tests with a synthetic secret and a temp store: valid → 204 + rows + `process` called after response; missing/mismatched → 401 + rejection row + `process` not called; not-a-list → 400, nothing stored; same delivery twice → 204 twice, one `events` row — `tests/test_web.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Signature computed over the local URL | 401 mismatch — only `HUBSPOT_WEBHOOK_URI` is signed |
| One event missing `eventId` in a valid delivery | that event logged + counted, others stored, 204 |
| Empty array `[]` | 204, delivery row with `event_count = 0` |
| Store not writable | 500 `delivery.not_persisted`, `process` not called |

## Definition of Done

- [ ] Endpoint tests above pass; the handler never calls processing inline (QG-3)
- [ ] `tests/test_smoke.py` unchanged and green
- [ ] No body, `propertyValue` or `sourceId` in logs or store
- [ ] `ruff check . && pytest` green
