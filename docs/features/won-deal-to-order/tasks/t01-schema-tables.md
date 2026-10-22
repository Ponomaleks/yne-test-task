---
id: T1
title: "Promote the four staged tables into app/schema.sql"
layer: "migration"
deps: []
blocks: ["T2"]
acs: ["AC-12", "AC-15"]
files_hint: ["docs/features/won-deal-to-order/migrations/01_create_deliveries.up.sql", "docs/features/won-deal-to-order/migrations/01_create_deliveries.down.sql", "docs/features/won-deal-to-order/migrations/02_create_events.up.sql", "docs/features/won-deal-to-order/migrations/02_create_events.down.sql", "docs/features/won-deal-to-order/migrations/03_create_outcomes.up.sql", "docs/features/won-deal-to-order/migrations/03_create_outcomes.down.sql", "docs/features/won-deal-to-order/migrations/04_create_rejections.up.sql", "docs/features/won-deal-to-order/migrations/04_create_rejections.down.sql", "app/schema.sql", "tests/test_store.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "M"
status: "todo"
step: ""
---

# T1 — Promote the four staged tables into app/schema.sql

## Place in the sequence

- **Blocked by:** — · **Blocks:** T2 — Add store functions · **Wave:** 1, no inputs needed.
- **Lane:** shares `tests/test_store.py` with T2 — serialized (T2 follows anyway). `layer: migration` is always serialized.

## Why (user story)

> **As an** Integration operator
> **I want** repeated deliveries, repeated events and failures of the CRM or the accounting system to never create a second order or lose an event
> **So that** I can replay and retry without fear
>
> — `spec.md §4, US-04, verbatim` · full text: [spec.md](../spec.md)

This task creates the tables that make an event unique by its event ID and keep every outcome and rejection.

## Inlined context

> **Store:** one local SQLite file, `app/schema.sql` applied at startup with `CREATE TABLE IF NOT
> EXISTS`, no migration tool.
>
> — `data-model.md` header, Store, verbatim · full text: [data-model.md](../data-model.md)

> Foreign keys are declared; SQLite enforces them only with `PRAGMA foreign_keys = ON` on each
> connection, so `app/store.py` sets it on every short-lived connection.
> Delete strategy: None. Rows are never deleted or updated; a schema change resets the file (ADR-0003).
>
> — `data-model.md §Conventions, Constraints + Delete strategy, abridged` · full text: [data-model.md](../data-model.md)

There is no live `migrations/` tree in this repo (ADR-0003): "promote" means appending the four
`*.up.sql` bodies, in order 01→04, to `app/schema.sql`. The `*.down.sql` files stay as the documented
reset path; nothing runs them.

> **Hard rule:** The store keeps event fields needed for processing only: no raw body, no `propertyValue`, no `sourceId`.
>
> — `sad.md §8, Personal data, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full
([data-model.md](../data-model.md) · [ADR-0003](../../../adr/0003-use-sqlite-file-store-with-startup-schema.md)) and follow it. Do not guess.

## Data delta

| Table | Key columns | Constraints | Change |
|---|---|---|---|
| `deliveries` | `id`, `request_timestamp` INTEGER, `body_sha256`, `event_count`, `received_at` | `CHECK (event_count >= 0)` | added |
| `events` | `event_id` INTEGER PK, `deal_id` TEXT, `subscription_type`, `property_name` NULL, `received_at` | PK = HubSpot `eventId` | added |
| `outcomes` | `id`, `event_id` FK, `deal_id`, `outcome`, `reason`, `dry_run`, `recorded_at` | `CHECK outcome IN (ordered, skipped, held, failed)`, `CHECK dry_run IN (0,1)`, FK → `events` | added |
| `rejections` | `id`, `request_timestamp` TEXT NULL, `body_sha256`, `reason`, `received_at` | — | added |
| index `idx_outcomes_event_id` | `outcomes(event_id)` | — | added |

— `data-model.md §Entities + §Indexes, abridged` · full text: [data-model.md](../data-model.md)

Staged pairs: `docs/features/won-deal-to-order/migrations/01_create_deliveries.up.sql` / `.down.sql`,
`02_create_events`, `03_create_outcomes`, `04_create_rejections`.

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

This task only provides the schema these ACs rely on (unique `event_id`, `rejections` table); behaviour is asserted in T2, T11, T12.

## Checklist

- [ ] Append the four `*.up.sql` bodies, in order, to `app/schema.sql`; keep `PRAGMA user_version = 1` — `app/schema.sql`
- [ ] Add a test: after `init_store`, the four tables and `idx_outcomes_event_id` exist (`sqlite_master`) — `tests/test_store.py`
- [ ] Add a test: inserting the same `event_id` twice with `INSERT OR IGNORE` leaves one row; an `outcome` outside the four values raises `sqlite3.IntegrityError` — `tests/test_store.py`

## Edge cases

| Case | Behaviour |
|---|---|
| `init_store` runs twice on the same file | no error, no change (existing test stays green) |
| `outcome = 'unknown'` or `dry_run = 2` | `CHECK` constraint rejects the insert |

## Definition of Done

- [ ] The staged tables are in `app/schema.sql`; `init_store` applies it twice to a fresh file without error
- [ ] New schema tests pass; the existing `test_schema_applies_twice_to_a_fresh_file` is unchanged and green
- [ ] every Hard Rule inlined above still holds
- [ ] `ruff check . && pytest` green
