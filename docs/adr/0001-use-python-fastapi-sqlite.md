---
status: Accepted
owner: "Oleksandr Ponomarenko"
reviewers: []
updated_at: "2026-10-22"
feature_size: "S"
ticket: ""
---

# 0001 — Use Python with FastAPI, httpx, sqlite3, pytest and ruff

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Oleksandr Ponomarenko (owner), with the survey foundation session

## Context

The repo is greenfield. The integration receives HubSpot webhook deliveries, reads the CRM, and
writes customers and Draft orders to PowerOffice. The task leaves language, framework and tools free
and allows a simple store (task text, brief §5). The assignment is time-boxed to 4 hours and
includes a live change in the interview, so the author must explain and change every line
(CLAUDE.md rule 8).

## Decision drivers

- The author can explain and change every line live (CLAUDE.md rule 8); the owner has Python and
  SQLite experience and no backend TypeScript experience.
- 4-hour time box: few dependencies, no build step, no infrastructure.
- Signature check over the raw request body (spec §6.1, AC-15).
- Reliable deduplication and atomic outcomes (spec AC-12, AC-13).
- Hermetic check command: in-process endpoint tests, faked HTTP clients, no network (CLAUDE.md).
- Validation of inbound payloads at the boundary (CLAUDE.md integration checklist).

## Considered options

1. **Python 3.14 + FastAPI + uvicorn + httpx + sqlite3 + pytest + ruff** — mainstream, owner's
   experience, standard-library store.
2. **TypeScript on Node 24 with built-ins** (native type stripping, node:http, fetch, node:sqlite,
   node:test, zod) — technically fine and probed locally, but not the owner's backend experience.
3. **TypeScript + Fastify + Vitest** — more framework features, more dependencies to explain.

## Decision outcome

**Chosen:** Option 1. It matches the owner's experience, which is the dominant driver under the
time box and the live-change interview. SQLite is in the standard library; a unique key on the event
ID and transactions give reliable deduplication and atomic outcomes. FastAPI gives raw body access
for the signature check, validation at the boundary and an in-process `TestClient`.
`httpx.MockTransport` fakes the external APIs without extra libraries.

Rules that come with it:
- Dependencies: fastapi, uvicorn, httpx; dev: pytest, ruff. No other dependencies.
- No ORM, no migration framework, no queue framework (ADR-0003).
- No async where it is not needed: sync endpoints and `httpx.Client`.
- Money is always `Decimal`, never `float`.
- The signature is computed over the raw request body, never a re-serialized one.
- Check command: `ruff check . && pytest`, hermetic. GitHub Actions CI runs the same check. No
  `test:integration` or `e2e` targets.
- The existing Node tooling is kept only for the secrets hook; prettier is not used for Python.

## Consequences

**Positive**
- The author can defend every line; fast iteration with no build step.
- Five dependencies in total (three runtime, two dev), all mainstream.
- In-process endpoint tests and faked clients keep the check hermetic.

**Negative**
- Python 3.14 support in FastAPI's dependency chain is not verified `[placeholder]`; if wheels are
  missing, fall back to Python 3.13.
- No static type check in the gate (no mypy, by the "no other dependencies" rule); type hints are
  documentation only.
- The repo carries two toolchains (Python for the app, Node for the Claude Code hook).

**Neutral**
- Switching language later is a rewrite; acceptable for a time-boxed assignment.

## Links

- Spec: [[../features/won-deal-to-order/spec.md]] §6, §6.1
- Architecture map: [[../architecture-map.md]] §Stack
- Related ADR: [[0002-separate-pure-core-from-io-edges]], [[0003-use-sqlite-file-store-with-startup-schema]]
