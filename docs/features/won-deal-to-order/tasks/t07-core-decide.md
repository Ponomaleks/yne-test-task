---
id: T7
title: "Decide skip and hold outcomes as pure rules"
layer: "domain"
deps: ["T4", "T5"]
blocks: ["T10"]
acs: ["AC-04", "AC-07", "AC-08", "AC-09", "AC-10", "AC-22"]
files_hint: ["app/core/decide.py", "tests/core/test_decide.py"]
owner: "Oleksandr Ponomarenko"
estimate: "M"
context_budget: "M"
status: "done"
step: "COMMIT"
---

# T7 — Decide skip and hold outcomes as pure rules

## Place in the sequence

- **Blocked by:** T4 — orgnr, T5 — won stages · **Blocks:** T10 — Process one event · **Wave:** 2.
- **Lane:** own lane.

## Why (user story)

> **As a** Finance reviewer
> **I want** deals the integration cannot match safely to be held for review with a plain reason
> **So that** no order is attached to a guessed customer
>
> — `spec.md §4, US-03, verbatim` · full text: [spec.md](../spec.md)

This task turns the current deal state into "skip", "hold with reason" or "orderable", with no I/O.

## Inlined context

> checks won from the pipeline configuration, in any pipeline → current stage not won: skipped.
> won, and a hold rule applies: normalizes the orgnr to nine digits, applies the hold rules.
> hold reasons: no company, several companies, foreign customer (before invalid orgnr), missing or invalid orgnr, no line items, no currency.
> After the customer lookup: several customers match → held, orgnr matches several customers.
>
> — `sad.md §6, Flow 3, steps after "reads the pipelines", abridged` · full text: [sad.md](../sad.md)

Reason strings are the spec's exact text (they appear in outcomes and the report): `current stage not won`,
`no company`, `several companies`, `foreign customer`, `missing or invalid orgnr`, `no line items`,
`no currency`, `orgnr matches several customers`.

Uses `normalize_orgnr` / `is_foreign` (T4, `app/core/orgnr.py`) and `is_won` (T5, `app/core/won.py`).

**Fallback:** insufficient → read [spec.md](../spec.md) §5 and [sad.md](../sad.md) §6 Flow 3. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-04 — cross-context

> **Given** an event says a deal moved to a won stage, but the deal's current stage in the CRM is not a won stage
> **When** the integration processes the event
> **Then** no order is created and the unit of work is recorded as skipped with the reason "current stage not won"
>
> — `spec.md §5, AC-04, verbatim` · full text: [spec.md](../spec.md)

### AC-07 — error

> **Given** a won deal whose company has no orgnr, or an orgnr that is not nine digits after normalization
> **When** the integration processes the event
> **Then** no customer and no order are created, and the deal is held for review with the reason "missing or invalid orgnr"
>
> — `spec.md §5, AC-07, verbatim` · full text: [spec.md](../spec.md)

### AC-08 — domain invariant

> **Given** a won deal whose company has a foreign registration prefix other than "NO", or a country other than Norway
> **When** the integration processes the event
> **Then** the prefix is never stripped to produce nine digits, no customer or order is created, and the deal is held for review with the reason "foreign customer"; this reason takes precedence over "missing or invalid orgnr" (AC-07)
>
> — `spec.md §5, AC-08, verbatim` · full text: [spec.md](../spec.md)

### AC-09 — domain invariant

> **Given** a won deal whose valid orgnr matches more than one existing customer
> **When** the integration processes the event
> **Then** no order is created and the deal is held for review with the reason "orgnr matches several customers"
>
> — `spec.md §5, AC-09, verbatim` · full text: [spec.md](../spec.md)

### AC-10 — domain invariant

> **Given** a won deal with more than one company, or with no company
> **When** the integration processes the event
> **Then** no order is created and the deal is held for review with the reason "several companies" or "no company"
>
> — `spec.md §5, AC-10, verbatim` · full text: [spec.md](../spec.md)

### AC-22 — error

> **Given** a won deal with no line items, or with no currency
> **When** the integration processes the event
> **Then** no order is created and the deal is held for review with the reason "no line items" or "no currency"
>
> — `spec.md §5, AC-22, verbatim` · full text: [spec.md](../spec.md)

## Checklist

- [ ] A small result type, e.g. `Decision(outcome: "skipped" | "held" | "orderable", reason: str, orgnr: str | None)` — `app/core/decide.py`
- [ ] `decide_deal(pipeline_id, stage_id, won, companies, line_items, currency) -> Decision` applying, in this order: not won → skipped; no company; several companies; foreign customer; missing or invalid orgnr; no line items; no currency; else orderable with the normalized orgnr — `app/core/decide.py`
- [ ] `decide_customer(matches: list) -> Decision`: >1 → held "orgnr matches several customers"; else orderable — `app/core/decide.py`
- [ ] Parametrized tests, one per reason and the precedence case, synthetic data only — `tests/core/test_decide.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Foreign prefix AND invalid digits | `foreign customer` (precedence) |
| Not won AND no company | `skipped`, `current stage not won` (won check first, flow 3) |
| Currency empty string | `no currency` |
| 0 or 1 customer match | orderable (0 → T10 creates the customer) |

## Definition of Done

- [ ] Unit tests for each reason, the precedence and the not-won-first order pass
- [ ] No I/O in `app/core/decide.py`
- [ ] `ruff check . && pytest` green
