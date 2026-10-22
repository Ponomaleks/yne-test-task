---
id: T4
title: "Normalize the orgnr and detect foreign registrations"
layer: "domain"
deps: []
blocks: ["T7"]
acs: ["AC-06", "AC-08"]
files_hint: ["app/core/orgnr.py", "tests/core/test_orgnr.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "S"
status: "todo"
step: ""
---

# T4 — Normalize the orgnr and detect foreign registrations

## Place in the sequence

- **Blocked by:** — · **Blocks:** T7 — Skip and hold rules · **Wave:** 1, pure, no inputs.
- **Lane:** own lane.

## Why (user story)

> **As a** Finance reviewer
> **I want** the order attached to the existing customer with the same orgnr, or to a new customer only when none exists
> **So that** customers are never created twice and invoices reach the right company
>
> — `spec.md §4, US-02, verbatim` · full text: [spec.md](../spec.md)

This task gives a single, exact orgnr to match customers by, and refuses to make one from a foreign number.

## Inlined context

> orgnr — the Norwegian organization number: exactly 9 digits after removing spaces, an optional "NO" prefix and an optional "MVA" suffix. NOT a foreign registration number, even if it has 9 digits after another prefix.
>
> — `CONTEXT.md §Glossary, orgnr, verbatim` · full text: [CONTEXT.md](../CONTEXT.md)

Synthetic shapes seen in the evidence (digit-masked): `999999999`, `999 999 999`, `NO 999 999 999 MVA`, `DE 999 999 999` with country `Germany`, and a missing orgnr (`null`) —
`evidence/api-hubspot-deals-summary.md` + `-2.md`, orgnr_mask, abridged.

**Fallback:** insufficient → read [spec.md](../spec.md) §5 and [CONTEXT.md](../CONTEXT.md). Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-06 — domain invariant

> **Given** a company orgnr written as nine digits, as digits with spaces, or with a "NO" prefix, an "MVA" suffix, or both
> **When** the integration reads the company
> **Then** it uses the nine digits as the orgnr, and any other result than exactly nine digits is treated as an invalid orgnr
>
> — `spec.md §5, AC-06, verbatim` · full text: [spec.md](../spec.md)

### AC-08 — domain invariant

> **Given** a won deal whose company has a foreign registration prefix other than "NO", or a country other than Norway
> **When** the integration processes the event
> **Then** the prefix is never stripped to produce nine digits, no customer or order is created, and the deal is held for review with the reason "foreign customer"; this reason takes precedence over "missing or invalid orgnr" (AC-07)
>
> — `spec.md §5, AC-08, verbatim` · full text: [spec.md](../spec.md)

This task owns the normalization and the "is foreign" check; the hold and its precedence are applied in T7.

## Checklist

- [ ] `normalize_orgnr(raw: str | None) -> str | None`: strip spaces, optional leading `NO`, optional trailing `MVA` (case-insensitive), return 9 digits or `None` — `app/core/orgnr.py`
- [ ] `is_foreign(raw: str | None, country: str | None) -> bool`: a letter prefix other than `NO`, or a country present and not Norway — `app/core/orgnr.py`
- [ ] Parametrized tests with synthetic numbers for every shape above — `tests/core/test_orgnr.py` (create empty `tests/core/__init__.py` if missing)

## Edge cases

| Case | Behaviour |
|---|---|
| `"DE 123 456 789"` | `is_foreign` true; `normalize_orgnr` never returns `123456789` for it |
| 8 or 10 digits, letters inside | `None` (invalid) |
| `None` or empty | `None` (invalid); not foreign unless the country is non-Norway |
| `"NO123456789MVA"` without spaces | `"123456789"` |

## Definition of Done

- [ ] Parametrized unit tests above pass
- [ ] `ruff check . && pytest` green
