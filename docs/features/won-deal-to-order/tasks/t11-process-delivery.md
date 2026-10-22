---
id: T11
title: "Process a delivery's events under one lock, counting duplicates and failures"
layer: "app"
deps: ["T10"]
blocks: ["T15"]
acs: ["AC-12", "AC-16", "AC-19"]
files_hint: ["app/processor.py", "tests/test_processor.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "M"
status: "done"
step: "COMMIT"
---

# T11 — Process a delivery's events under one lock, counting duplicates and failures

## Place in the sequence

- **Blocked by:** T10 — Process one event · **Blocks:** T15 — Config and CLI wiring · **Wave:** 4.
- **Lane:** shares `app/processor.py` + `tests/test_processor.py` with T10 — serialized.

## Why (user story)

> **As an** Integration operator
> **I want** every event to end in exactly one recorded outcome with a reason, and a summary per run
> **So that** I can see what was ordered, skipped, held or failed
>
> — `spec.md §4, US-06, verbatim` · full text: [spec.md](../spec.md)

This task is the background-task entry: loop the delivery's events, skip duplicates, isolate failures, log one summary.

## Inlined context

> The background task processes only the events of its own delivery. An event with no outcome or whose last outcome is failed is processed. An event with a final outcome is counted as a duplicate event.
> One process-wide lock: only one background task processes at a time, and uvicorn runs one worker. Without it, two deliveries of the same deal processed at the same time could both find no order and both create one.
>
> — `adr/0004, Decision outcome, abridged` · full text: [ADR-0004](../adr/0004-process-events-in-a-background-task-and-retry-by-replay.md)

> loop each event of the delivery: reads the last outcome → final outcome already recorded: counts a duplicate event, records nothing new / no outcome yet, failed or dry-run: processes the event as in flow 3 → the event fails: records the outcome failed with the reason, goes on with the next event.
> logs the delivery summary with counts per outcome and duplicate events, releases the lock.
>
> — `sad.md §6, Flow 4, background part, abridged` · full text: [sad.md](../sad.md)

> Observability — Structured key=value log lines per delivery (ID, event count, duration, status) and per event (event ID, deal ID, outcome, reason).
>
> — `sad.md §7, Monitoring, abridged` · full text: [sad.md](../sad.md)

Uses `has_final_outcome`, `record_outcome` (T2) and `process_event` (T10).

**Fallback:** insufficient → read [sad.md](../sad.md) §6 Flows 2 and 4 and ADR-0004. Do not guess.

## Data delta

| Table | Change |
|---|---|
| `outcomes` | read last row per event; insert `failed` on an unexpected exception |

— `data-model.md §Entities outcomes, abridged` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-12 — domain invariant

> **Given** an event that already has a final outcome (ordered, skipped or held for review), or a won event for a deal that already has its Draft sales order
> **When** that event arrives again, or the other won event is processed
> **Then** the event with a final outcome keeps that outcome as its only recorded outcome, and the run summary counts it as "duplicate event"; the won event for a deal with an order creates no second order and is recorded as skipped with the reason "order already exists", found by the deal's external key (AC-13), not by the event ID; an event whose last outcome is failed is not a duplicate and is processed again; an amount event for a deal that already has its order gets the reason "change after order, not handled" instead (AC-16)
>
> — `spec.md §5, AC-12, verbatim` · full text: [spec.md](../spec.md)

### AC-16 — happy

> **Given** a delivery with several events, where one event is a lost deal, one is a new deal in an early stage, one is an amount change on a deal that already has an order, and one fails
> **When** the integration processes the delivery
> **Then** each event gets its own outcome with a reason ("current stage not won", "current stage not won", "change after order, not handled", "failed: <reason>"), and the failing event does not stop the other events
>
> — `spec.md §5, AC-16, verbatim` · full text: [spec.md](../spec.md)

### AC-19 — happy

> **Given** persisted units of work from an earlier run, some failed for a technical reason and some held for review
> **When** the integration operator replays the recorded deliveries again (there is no separate retry action in this slice)
> **Then** each failed unit of work is decided again from the deal's current state and ends in a new recorded outcome without a duplicate customer or order (AC-12, AC-13); held units of work keep their outcome and reason and stay persisted for the finance reviewer
>
> — `spec.md §5, AC-19, verbatim` · full text: [spec.md](../spec.md)

## Checklist

- [ ] Module-level `threading.Lock`; `process_delivery(delivery_id, events, *, hubspot, poweroffice, store_path, dry_run)` holds it for the whole loop — `app/processor.py`
- [ ] Per event: `has_final_outcome` → count duplicate; else `process_event`; any exception → `record_outcome(..., "failed", f"failed: {type(e).__name__}")`, continue — `app/processor.py`
- [ ] One summary log line: `delivery=<id> events=<n> ordered= skipped= held= failed= duplicate= duration_ms=` — `app/processor.py`
- [ ] Tests: AC-16 mixed delivery; same delivery twice → second run all duplicates, no new rows; failed then success on re-run; held stays held; two threads on the same deal create one order — `tests/test_processor.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Same event twice inside one delivery | second is a duplicate if the first got a final outcome |
| Blocking auth error from PowerOffice | recorded failed per event; the rest of the run continues (no event left without an outcome) |
| Last outcome is a dry-run `ordered` | processed again (dry run is never final) |

## Definition of Done

- [ ] Tests above pass, incl. the two-thread one-order test (sad §11 High risk)
- [ ] Summary log line holds counts and IDs only
- [ ] `ruff check . && pytest` green
