---
id: T6
title: "Map a deal and its line items to a Draft order with percentage discounts"
layer: "domain"
deps: []
blocks: ["T10"]
acs: ["AC-01", "AC-20", "AC-21"]
files_hint: ["app/core/order.py", "tests/core/test_order.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "M"
status: "todo"
step: ""
---

# T6 — Map a deal and its line items to a Draft order with percentage discounts

## Place in the sequence

- **Blocked by:** — · **Blocks:** T10 — Process one event · **Wave:** 1, pure, no inputs.
- **Lane:** own lane.

## Why (user story)

> **As a** Finance reviewer
> **I want** each won deal to appear as one Draft sales order with the deal's line items, discounts and currency
> **So that** I can review and invoice it without re-keying anything
>
> — `spec.md §4, US-01, verbatim` · full text: [spec.md](../spec.md)

This task builds the order payload; nothing is sent here.

## Inlined context

> Money and rounding — `Decimal` throughout. Discount per unit becomes a percentage of the unit price, rounded half up to two decimals, and the outcome notes the rounding (AC-21).
> Idempotency — order by external key `hubspot-deal-<dealId>` with exact equality.
>
> — `sad.md §8, Money and rounding + Idempotency, abridged` · full text: [sad.md](../sad.md)

> Line items carry no currency of their own, the deal does.
>
> — `spec.md §1, Traceability, Evidence facts, abridged` · full text: [spec.md](../spec.md)

Order payload fields (accounting-system docs): `customerId`, `reference` (≤ 50 chars, searchable),
`currencyCode`, `lines[]` with `description`, `quantity`, `unitPrice`, `discountPercent`. New orders
are `Draft` and not invoiced until finance reviews them. —
`docs/interview-reference/task/yne-api-uk.md §PowerOffice, POST /v2/SalesOrders, abridged` (git-ignored task doc).

Line item fields (all strings in the CRM): `name`, `price`, `quantity`, `discount` (currency per unit, may be `null`) —
`evidence/api-hubspot-deals-summary.md, property_types, abridged`.

**Fallback:** insufficient → read [sad.md](../sad.md) §8 and the task doc section above. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface. Produces the body of `POST /v2/SalesOrders`, sent by T9.

## Acceptance criteria

### AC-01 — happy

> **Given** a deal whose current stage is a won stage, with one company that has a valid orgnr matching exactly one existing customer, and at least one line item
> **When** the integration processes an event for that deal
> **Then** the accounting system holds one Draft sales order for that customer with one order line per line item (description, quantity, unit price, discount), the deal's currency and the deal's external key, and the unit of work is recorded as ordered
>
> — `spec.md §5, AC-01, verbatim` · full text: [spec.md](../spec.md)

### AC-20 — domain invariant

> **Given** any won deal processed by the integration
> **When** its order is created
> **Then** the order stays a Draft for finance review and no invoice is ever sent
>
> — `spec.md §5, AC-20, verbatim` · full text: [spec.md](../spec.md)

### AC-21 — domain invariant

> **Given** a line item with a discount stated in currency per unit
> **When** its order line is created
> **Then** the discount is carried over as a percentage of the unit price and is never dropped; if the percentage cannot represent the discount exactly, the line uses the nearest percentage with two decimals and the outcome notes the rounding
>
> — `spec.md §5, AC-21, verbatim` · full text: [spec.md](../spec.md)

This task owns the line mapping, currency, external key and discount math; T10 sends it and records "ordered".

## Checklist

- [ ] `external_key(deal_id: str) -> str` → `"hubspot-deal-<dealId>"` — `app/core/order.py`
- [ ] `discount_percent(unit_price: Decimal, discount: Decimal | None) -> tuple[Decimal, bool]` (percent, rounded?) with `ROUND_HALF_UP` to 2 decimals — `app/core/order.py`
- [ ] `build_order(deal_id, currency, line_items, customer_id) -> tuple[dict, bool]`: one line per item, `Decimal` amounts, no status/invoice field — `app/core/order.py`
- [ ] Tests with synthetic line items: exact percent, rounded percent (flag true), `null` discount → 0, multiple lines keep order — `tests/core/test_order.py` (create empty `tests/core/__init__.py` if missing)

## Edge cases

| Case | Behaviour |
|---|---|
| `discount` is `null` | `discountPercent` 0, not rounded |
| Discount 100 on price 300 | 33.33, rounded flag true |
| Unit price 0 with a discount | not in the spec (assumption, confirm at review): raise `ValueError`; T10 records it as failed with the error type |
| JSON serialization of `Decimal` | the client (T9) serializes; this module returns `Decimal`, never float |

## Definition of Done

- [ ] Unit tests above pass
- [ ] No I/O in `app/core/order.py`; no invoice or status field produced
- [ ] `ruff check . && pytest` green
