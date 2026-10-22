---
id: T5
title: "Resolve won stages from the pipeline configuration"
layer: "domain"
deps: []
blocks: ["T7"]
acs: ["AC-04", "AC-05"]
files_hint: ["app/core/won.py", "tests/core/test_won.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "S"
status: "done"
step: "COMMIT"
---

# T5 — Resolve won stages from the pipeline configuration

## Place in the sequence

- **Blocked by:** — · **Blocks:** T7 — Skip and hold rules · **Wave:** 1, pure, no inputs.
- **Lane:** own lane.

## Why (user story)

> **As a** Sales representative
> **I want** a deal marked won in any pipeline to be picked up
> **So that** I do not need extra steps for deals outside the default pipeline
>
> — `spec.md §4, US-07, verbatim` · full text: [spec.md](../spec.md)

This task decides "won" from pipeline metadata, never from a stage name.

## Inlined context

> Won stage — a pipeline stage that is closed with probability 1.0, in any pipeline. NOT only the stage named "closedwon".
>
> — `CONTEXT.md §Glossary, Won stage, verbatim` · full text: [CONTEXT.md](../CONTEXT.md)

> All `isClosed` and `probability` values are strings. Stages: `default/closedwon` "true"/"1.0";
> `default/closedlost` "true"/"0.0"; `84512397/84512400` "true"/"1.0"; `84512397/84512401` "true"/"0.0"; open stages "false".
>
> — `evidence/api-hubspot-pipelines.md §Stages, abridged` · full text: [evidence](../../../../evidence/api-hubspot-pipelines.md)

Response shape: `results[]` → `id`, `stages[]` → `id`, `metadata.isClosed`, `metadata.probability` (strings). Compare probability as `Decimal`, not float.

**Fallback:** insufficient → read the evidence file and [spec.md](../spec.md) §5. Do not guess.

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

### AC-05 — cross-context

> **Given** a deal whose current stage is closed with probability 1.0 in a pipeline other than the default one
> **When** the integration processes an event for that deal
> **Then** the deal is treated as won, exactly as a deal in the default pipeline's won stage
>
> — `spec.md §5, AC-05, verbatim` · full text: [spec.md](../spec.md)

## Checklist

- [ ] `won_stages(pipelines: list[dict]) -> set[tuple[str, str]]` of (pipeline id, stage id) where `isClosed == "true"` and `Decimal(probability) == 1` — `app/core/won.py`
- [ ] `is_won(pipeline_id, stage_id, won: set) -> bool` — `app/core/won.py`
- [ ] Tests with a synthetic two-pipeline fixture shaped like the evidence — `tests/core/test_won.py` (create empty `tests/core/__init__.py` if missing)

## Edge cases

| Case | Behaviour |
|---|---|
| `closedlost` (closed, 0.0) | not won |
| `contractsent` (open, 0.9) | not won |
| Stage id unknown to the configuration | not won |
| `probability` "1" vs "1.0" | both won (`Decimal` compare) |

## Definition of Done

- [ ] Unit tests above pass, incl. the non-default pipeline stage
- [ ] `ruff check . && pytest` green
