---
id: T10
title: "Process one event from the current deal state to one outcome"
layer: "app"
deps: ["T2", "T6", "T7", "T8", "T9"]
blocks: ["T11"]
acs: ["AC-01", "AC-02", "AC-03", "AC-09", "AC-11", "AC-13", "AC-18", "AC-20"]
files_hint: ["app/processor.py", "tests/test_processor.py"]
owner: "Oleksandr Ponomarenko"
estimate: "M"
context_budget: "M"
status: "done"
step: "COMMIT"
---

# T10 — Process one event from the current deal state to one outcome

## Place in the sequence

- **Blocked by:** T2 — store, T6 — order mapping, T7 — decide rules, T8 — HubSpot client, T9 — PowerOffice client · **Blocks:** T11 — Process a delivery · **Wave:** 3.
- **Lane:** shares `app/processor.py` + `tests/test_processor.py` with T11 — serialized.

## Why (user story)

> **As a** Finance reviewer
> **I want** each won deal to appear as one Draft sales order with the deal's line items, discounts and currency
> **So that** I can review and invoice it without re-keying anything
>
> — `spec.md §4, US-01, verbatim` · full text: [spec.md](../spec.md)

This task is the imperative shell for one unit of work: read, decide, look up, create, record one outcome.

## Inlined context

> `processor.py` is the shell for one unit of work: it reads through the clients, calls the core, writes through the clients and records the outcome. Clients are passed into the processor as plain arguments, so tests pass fakes.
>
> — `sad.md §5, intro, abridged` · full text: [sad.md](../sad.md)

> reads the current deal, never the event's property value → deal does not exist: held, deal not found.
> reads the pipelines, companies and line items → checks won → not won: skipped / hold rule: held.
> won and orderable: maps line items → looks up the order by the external key → exists: skipped, order already exists (an amount event gets change after order, not handled).
> no order: looks up the customer by the normalized orgnr → several: held / dry run: records a dry-run outcome with the customer and order it would create / one: creates the Draft order / none: creates the customer, then the Draft order → ordered, notes any discount rounding.
> the accounting system fails or does not answer on any create above → failed with the error type, kept for the next replay.
>
> — `sad.md §6, Flow 3, abridged` · full text: [sad.md](../sad.md)

> Dry run — All reads and decisions run, and the outcome records what would be created. No write to PowerOffice. Dry-run outcomes are marked and never count as final.
>
> — `sad.md §8, Dry run, verbatim` · full text: [sad.md](../sad.md)

> **Hard rule:** outcomes carry technical IDs, counts, statuses and reasons only.
>
> — `spec.md §6.1, Personal data touched, abridged` · full text: [spec.md](../spec.md)

Collaborators: `app/store.py` `record_outcome` (T2); `app/core/decide.py` `decide_deal`, `decide_customer` (T7); `app/core/won.py` (T5); `app/core/order.py` `build_order`, `external_key` (T6); `HubSpotClient` (T8); `PowerOfficeClient` (T9).

**Fallback:** insufficient → read [sad.md](../sad.md) §6 Flow 3 and [spec.md](../spec.md) §5. Do not guess.

## Data delta

| Table | Change |
|---|---|
| `outcomes` | one insert per call: `outcome`, `reason`, `dry_run` |

— `data-model.md §Entities outcomes, abridged` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-01 — happy

> **Given** a deal whose current stage is a won stage, with one company that has a valid orgnr matching exactly one existing customer, and at least one line item
> **When** the integration processes an event for that deal
> **Then** the accounting system holds one Draft sales order for that customer with one order line per line item (description, quantity, unit price, discount), the deal's currency and the deal's external key, and the unit of work is recorded as ordered
>
> — `spec.md §5, AC-01, verbatim` · full text: [spec.md](../spec.md)

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

### AC-09 — domain invariant

> **Given** a won deal whose valid orgnr matches more than one existing customer
> **When** the integration processes the event
> **Then** no order is created and the deal is held for review with the reason "orgnr matches several customers"
>
> — `spec.md §5, AC-09, verbatim` · full text: [spec.md](../spec.md)

### AC-11 — error

> **Given** an event names a deal that the CRM reports as not existing
> **When** the integration processes the event
> **Then** the unit of work is held for review with the reason "deal not found" and is not retried automatically
>
> — `spec.md §5, AC-11, verbatim` · full text: [spec.md](../spec.md)

### AC-13 — error

> **Given** the accounting system fails or does not answer while an order is being created
> **When** the integration handles that failure
> **Then** the unit of work is recorded as failed with the reason and stays persisted, and a retry first checks for an existing order with the deal's external key and creates one only if none is found
>
> — `spec.md §5, AC-13, verbatim` · full text: [spec.md](../spec.md)

### AC-18 — happy

> **Given** the integration runs in dry-run mode
> **When** the integration operator replays deliveries
> **Then** every unit of work gets the outcome it would have, including the customer and order it would create, and nothing is written to the accounting system
>
> — `spec.md §5, AC-18, verbatim` · full text: [spec.md](../spec.md)

### AC-20 — domain invariant

> **Given** any won deal processed by the integration
> **When** its order is created
> **Then** the order stays a Draft for finance review and no invoice is ever sent
>
> — `spec.md §5, AC-20, verbatim` · full text: [spec.md](../spec.md)

## Checklist

- [ ] `process_event(event, *, hubspot, poweroffice, store_path, dry_run) -> Outcome` following flow 3 in order — `app/processor.py`
- [ ] `DealNotFound` → held "deal not found"; `decide_deal` skip/hold → record as is — `app/processor.py`
- [ ] Order lookup by `external_key`: found → skipped "order already exists", or "change after order, not handled" when `property_name == "amount"` — `app/processor.py`
- [ ] Customer lookup → `decide_customer`; dry run → `ordered` with `dry_run=1` and a reason naming "would create customer"/"would create order <key>" (technical IDs only) — `app/processor.py`
- [ ] Create customer (if none) then order; reason for ordered carries the PowerOffice order ID and "discount rounded" when T6 flags it; any accounting error → `failed: <ErrorType>` — `app/processor.py`
- [ ] Tests with fake clients (plain classes or MockTransport) and a temp store: one per AC above plus "amount event after order" — `tests/test_processor.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Create customer succeeds, create order times out | `failed: <ErrorType>`; next run finds the customer by orgnr (no second customer) |
| Order create timed out but the order exists | next run: lookup finds it → skipped "order already exists" (sad §11) |
| Dry run with no customer | no POST at all; outcome `ordered`, `dry_run=1` |
| HubSpot read fails after retries | `failed: <ErrorType>` (not held) |

## Definition of Done

- [ ] Processor tests for every AC listed pass with fake clients; a dry-run test asserts zero POSTs
- [ ] No personal value in outcomes or logs (assert in one test that the company name is not in the reason)
- [ ] `ruff check . && pytest` green
