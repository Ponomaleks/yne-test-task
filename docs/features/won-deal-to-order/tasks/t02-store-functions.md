---
id: T2
title: "Add store functions for deliveries, events, outcomes and rejections"
layer: "infra"
deps: ["T1"]
blocks: ["T10", "T12", "T14"]
acs: ["AC-12", "AC-15"]
files_hint: ["app/store.py", "tests/test_store.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "M"
status: "done"
step: "COMMIT"
---

# T2 — Add store functions for deliveries, events, outcomes and rejections

## Place in the sequence

- **Blocked by:** T1 — Promote the staged tables · **Blocks:** T10 — Process one event, T12 — Webhook endpoint, T14 — Report module · **Wave:** 2.
- **Lane:** shares `tests/test_store.py` with T1 — serialized.

## Why (user story)

> **As an** Integration operator
> **I want** every event to end in exactly one recorded outcome with a reason, and a summary per run
> **So that** I can see what was ordered, skipped, held or failed
>
> — `spec.md §4, US-06, verbatim` · full text: [spec.md](../spec.md)

This task gives every other module one place to persist deliveries, events, outcomes and rejections.

## Inlined context

> - **Aggregates.** `deliveries` and `rejections` are standalone receipt logs. `events` is the
>   aggregate root of a unit of work; `outcomes` belong to it (append-only, one row per attempt; the
>   row with the highest `id` is the event's outcome).
> - **Timestamps.** `INTEGER` epoch milliseconds. Only `received_at` / `recorded_at`; no `updated_at`, because no row is ever updated.
> - `app/store.py` sets `PRAGMA foreign_keys = ON` on every short-lived connection.
>
> — `data-model.md §Conventions, abridged` · full text: [data-model.md](../data-model.md)

> `events`: One row per distinct event ID, inserted with `INSERT OR IGNORE`, so a repeated event keeps its first row.
> `outcomes`: A final outcome (ordered, skipped or held, with `dry_run = 0`) is never followed by another row; a `failed` or dry-run row is.
> Last outcome: `SELECT ... FROM outcomes WHERE event_id = ? ORDER BY id DESC LIMIT 1`.
>
> — `data-model.md §Entities events/outcomes + §Indexes, abridged` · full text: [data-model.md](../data-model.md)

Existing pattern to follow: `app/store.py` `init_store(path)` opens a short-lived `sqlite3.connect`
per operation (connections are bound to their thread; processing runs in a background thread).

> **Hard rule:** Personal data — Not in logs, outcomes or the store. A rejection is stored with the request timestamp header and a SHA-256 of the body.
>
> — `sad.md §8, Personal data, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient or contradicted by the code → read [data-model.md](../data-model.md) in full and follow it. Do not guess.

## Data delta

| Table | Access | Change |
|---|---|---|
| `deliveries` | insert, returns `id` | read/write |
| `events` | `INSERT OR IGNORE` by `event_id` | read/write |
| `outcomes` | insert; last row per `event_id`; last row per event for all events (report) | read/write |
| `rejections` | insert | write |

— `data-model.md §Entities, access patterns, abridged` · full text: [data-model.md](../data-model.md). No schema change in this task.

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-12 — domain invariant

> **Given** an event that already has a final outcome (ordered, skipped or held for review), or a won event for a deal that already has its Draft sales order
> **When** that event arrives again, or the other won event is processed
> **Then** the event with a final outcome keeps that outcome as its only recorded outcome, and the run summary counts it as "duplicate event"; the won event for a deal with an order creates no second order and is recorded as skipped with the reason "order already exists", found by the deal's external key (AC-13), not by the event ID; an event whose last outcome is failed is not a duplicate and is processed again; an amount event for a deal that already has its order gets the reason "change after order, not handled" instead (AC-16)
>
> — `spec.md §5, AC-12, verbatim` · full text: [spec.md](../spec.md)

### AC-15 — authorization

> **Given** a delivery whose signature is missing or does not match the delivery content
> **When** the integration receives it
> **Then** the delivery is rejected, none of its events are processed, and the rejection is recorded with the delivery's technical identity only
>
> — `spec.md §5, AC-15, verbatim` · full text: [spec.md](../spec.md)

This task owns the storage half: a repeated event keeps one row, and a "final outcome" check the processor uses.

## Checklist

- [ ] `save_delivery(path, request_timestamp, body_sha256, event_count) -> int` — `app/store.py`
- [ ] `save_events(path, events)`: `INSERT OR IGNORE` of (`event_id`, `deal_id` as text, `subscription_type`, `property_name`) — `app/store.py`
- [ ] `save_rejection(path, request_timestamp: str | None, body_sha256, reason)` — `app/store.py`
- [ ] `record_outcome(path, event_id, deal_id, outcome, reason, dry_run)` and `last_outcome(path, event_id)` returning the latest row or `None` — `app/store.py`
- [ ] `has_final_outcome(path, event_id) -> bool`: last row is ordered/skipped/held with `dry_run = 0` — `app/store.py`
- [ ] `last_outcomes(path)`: last outcome per event, ordered by `event_id` (for T14) — `app/store.py`
- [ ] `PRAGMA foreign_keys = ON` on every connection; tests with `init_store(tmp_path / "store.sqlite3")` and synthetic IDs — `tests/test_store.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Same event saved twice | one `events` row; first `received_at` kept |
| Last outcome is `failed` | `has_final_outcome` is false |
| Last outcome is `ordered` with `dry_run = 1` | `has_final_outcome` is false (dry run is never final) |
| Event with no outcome | `last_outcome` returns `None`, `has_final_outcome` false |
| Outcome for an unknown `event_id` | FK violation raises (foreign keys on) |

## Definition of Done

- [ ] Unit tests for each function pass against a temporary store, including the four edge cases above
- [ ] every Hard Rule inlined above still holds (no body, no `propertyValue`, no `sourceId` stored)
- [ ] `ruff check . && pytest` green
