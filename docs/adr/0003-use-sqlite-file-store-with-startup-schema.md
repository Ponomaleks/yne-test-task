---
status: Accepted
owner: "Oleksandr Ponomarenko"
reviewers: []
updated_at: "2026-10-22"
feature_size: "S"
ticket: ""
---

# 0003 — Use a local SQLite file store with a schema applied at startup

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Oleksandr Ponomarenko (owner), with the survey foundation session

## Context

Events must be persisted before the fast acknowledgement, deduplicated by event ID, and every
event must end in one recorded outcome; failed and held units of work stay persisted for a replay
(spec AC-12, AC-13, AC-19, §6). The task allows a simple queue and store (SQLite or a file) with a
written note on what production would use (brief §5).

## Decision drivers

- Deduplication by event ID and atomic outcome writes (spec AC-12, AC-13).
- Nothing lost between runs (spec §2, AC-19).
- No infrastructure and no extra dependencies (ADR-0001, 4-hour time box).
- Hermetic tests: a temporary SQLite file or `:memory:` per test.

## Considered options

1. **SQLite file via `sqlite3`, plain SQL, `schema.sql` applied at startup** — standard library,
   unique keys and transactions.
2. **JSON files on disk** — no constraints or transactions; deduplication and atomicity by hand.
3. **PostgreSQL + a migration tool** — production-grade, but needs a server or container and breaks
   the hermetic check.

## Decision outcome

**Chosen:** Option 1. A unique key on the event ID and one transaction per outcome give reliable
deduplication and atomic outcomes with the standard library. No ORM, no migration framework, no
queue framework: `app/schema.sql` uses `CREATE TABLE IF NOT EXISTS` and runs at startup. Tables are
decided in design / data-model.

Production would use PostgreSQL and a managed queue with an outbox pattern. That is a known
limitation, documented, not work in this assignment.

## Consequences

**Positive**
- Zero infrastructure; the store is one git-ignored file.
- Tests use temporary databases and stay hermetic.

**Negative**
- No migrations: a schema change during the assignment means deleting the local file.
- Single writer: no concurrent processors.

**Neutral**
- Moving to PostgreSQL later keeps the SQL mostly portable; the outbox needs new code.

## Links

- Spec: [[../features/won-deal-to-order/spec.md]] §2, AC-12, AC-13, AC-19
- Architecture map: [[../architecture-map.md]] §Datastores
- Related ADR: [[0001-use-python-fastapi-sqlite]]
