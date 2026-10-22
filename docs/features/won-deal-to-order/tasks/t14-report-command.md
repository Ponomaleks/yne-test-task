---
id: T14
title: "Print the run report from the store"
layer: "ports"
deps: ["T2"]
blocks: ["T15"]
acs: ["AC-17"]
files_hint: ["app/report.py", "tests/test_report.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "S"
status: "todo"
step: ""
---

# T14 — Print the run report from the store

## Place in the sequence

- **Blocked by:** T2 — store · **Blocks:** T15 — Config and CLI wiring · **Wave:** 3.
- **Lane:** own lane. Droppable if time runs out (sad §11 accepted debt): the run summary then is the per-delivery log line only.

## Why (user story)

> **As an** Integration operator
> **I want** every event to end in exactly one recorded outcome with a reason, and a summary per run
> **So that** I can see what was ordered, skipped, held or failed
>
> — `spec.md §4, US-06, verbatim` · full text: [spec.md](../spec.md)

This task prints the per-run summary the owner reads after a replay.

## Inlined context

> Run summary — `python -m app report` after a replay: counts per outcome (ordered, skipped, held, failed) and one line per event: `event=<id> deal=<id> outcome=<o> reason="<r>"` (the last outcome of each event). No personal values. Duplicate events are only in the logs.
>
> — `sad.md §8, Run summary, abridged` · full text: [sad.md](../sad.md)

> `report` — Prints the run summary from the store. Exit `1` when the store cannot be opened.
>
> — `contracts/cli.md, Commands, report, abridged` · full text: [cli.md](../contracts/cli.md)

Uses `last_outcomes(path)` from T2. Dry-run rows should be visible as such (e.g. `dry_run=1` on the line) so the owner does not read them as real orders.

**Fallback:** insufficient → read [sad.md](../sad.md) §8. Do not guess.

## Data delta

| Table | Change |
|---|---|
| `outcomes` | read-only: last row per event |

— `data-model.md §Entities outcomes, abridged` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface (CLI output only).

## Acceptance criteria

### AC-17 — happy

> **Given** the recorded deliveries of the test CRM
> **When** the integration operator replays them all, and then replays them all a second time
> **Then** the first replay creates orders for deals 40211700201, 40211700202, 40211700203 and 40211700206 (one each, although 40211700201 is delivered twice), holds 40211700204, 40211700205 and 40211700209, and skips 40211700207, 40211700208 and 40211700210; the second replay creates no customer and no order. The table matches the accounting-system probes (§1 traceability): no orgnr in it matches several existing customers, so AC-09 turns none of these orders into holds
>
> — `spec.md §5, AC-17, verbatim` · full text: [spec.md](../spec.md)

## Checklist

- [ ] `format_report(rows) -> str` (pure) and `print_report(store_path)` — `app/report.py`
- [ ] Tests: temp store with synthetic events and outcomes (incl. a failed then ordered event) → counts use the last outcome; line format exact — `tests/test_report.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Empty store | counts all 0, no event lines |
| Event with no outcome yet | listed as `outcome=none` so a stranded event is visible (QG-2) |

## Definition of Done

- [ ] Tests above pass
- [ ] Output carries IDs, outcomes and reasons only
- [ ] `ruff check . && pytest` green
