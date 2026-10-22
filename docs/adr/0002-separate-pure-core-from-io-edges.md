---
status: Accepted
owner: "Oleksandr Ponomarenko"
reviewers: []
updated_at: "2026-10-22"
feature_size: "S"
ticket: ""
---

# 0002 — Separate a pure core from the I/O edges in one flat package

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Oleksandr Ponomarenko (owner), with the survey foundation session

## Context

Most of the feature's risk sits in decision rules: the won check, orgnr normalization, hold
reasons, discount conversion and the order mapping (spec AC-04 to AC-11, AC-21, AC-22). CLAUDE.md
asks for pure core logic, I/O only at the edges, and abstractions only at external system
boundaries. The code must stay small enough to explain live.

## Decision drivers

- Most tests target mapping and validation (CLAUDE.md "Tests").
- Abstractions only at HTTP client boundaries; no DI frameworks, repositories or plugin systems
  (CLAUDE.md "Engineering principles").
- One responsibility per module; readable by the author (CLAUDE.md rule 8).

## Considered options

1. **Functional core, imperative shell in one flat package** — `app/core/` pure; `app/clients/`,
   `app/store.py`, `app/web.py`, `app/config.py`, `app/__main__.py` at the edges.
2. **Hexagonal layers** (`domain/`, `application/`, `infrastructure/`, `ports/`) — more ceremony
   and interfaces than one feature needs.
3. **Single module script** — fastest to write, but mixes I/O with rules and makes unit tests hard.

## Decision outcome

**Chosen:** Option 1. It gives pure, unit-testable rules and fakeable clients with the least
structure. Clients are passed into the processor as plain arguments, so tests pass fakes built on
`httpx.MockTransport`. Concrete files inside `app/core/` are decided in design.

## Consequences

**Positive**
- Hold and mapping rules are tested without fakes or a database.
- Few files; every module has one job.

**Negative**
- No formal port interfaces: if a third external system appears, the boundaries need more thought.

**Neutral**
- Moving to hexagonal layers later is a file move, not a rewrite, because the core is already pure.

## Links

- Spec: [[../features/won-deal-to-order/spec.md]] §5
- Architecture map: [[../architecture-map.md]] §Module inventory
- Related ADR: [[0001-use-python-fastapi-sqlite]]
