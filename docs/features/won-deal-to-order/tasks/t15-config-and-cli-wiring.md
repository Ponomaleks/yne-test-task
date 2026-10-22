---
id: T15
title: "Load config once and wire serve, replay and report commands"
layer: "wiring"
deps: ["T11", "T12", "T13", "T14"]
blocks: []
acs: ["AC-18"]
files_hint: ["app/config.py", "app/__main__.py", "tests/test_config.py", "tests/test_main.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "S"
status: "done"
step: "COMMIT"
---

# T15 — Load config once and wire serve, replay and report commands

## Place in the sequence

- **Blocked by:** T11 — Process a delivery, T12 — Webhook endpoint, T13 — Replay, T14 — Report · **Blocks:** — · **Wave:** 5, last.
- **Lane:** own lane.

## Why (user story)

> **As an** Integration operator
> **I want** a dry run that decides every outcome but writes nothing to the accounting system
> **So that** I can check the result before the real run
>
> — `spec.md §4, US-08, verbatim` · full text: [spec.md](../spec.md)

This task makes the dry run the default and gives the operator the three commands.

## Inlined context

> Configuration — Loaded and validated once in `config.py`; fails with missing variable names, never values. `DRY_RUN` defaults to true, so writes stay off until it is set to false.
>
> — `sad.md §8, Configuration, verbatim` · full text: [sad.md](../sad.md)

> Entry point: `python -m app <command>` (argparse). No command has options. Exit `0` finished; `1` blocking failure (missing configuration — variable names only, authentication rejected, system unreachable, store not readable); `2` usage error. `serve` runs on `127.0.0.1:8000`, one uvicorn worker.
>
> — `contracts/cli.md, abridged` · full text: [cli.md](../contracts/cli.md)

Variables (names from `.env.example`): `HUBSPOT_BASE_URL`, `HUBSPOT_APP_TOKEN`, `HUBSPOT_WEBHOOKS_SECRET`, `HUBSPOT_WEBHOOK_URI`, `POWEROFFICE_BASE_URL`, `POWEROFFICE_CLIENT_ID`, `POWEROFFICE_CLIENT_SECRET`, `DRY_RUN`. Store path: a git-ignored file under `data/` (scaffold `.gitignore`).
Constraint: `tests/test_smoke.py` asserts `main([]) == 0` — keep that; never edit the test.

**Fallback:** insufficient → read [cli.md](../contracts/cli.md) and [sad.md](../sad.md) §8. Do not guess.

## Data delta

No DB changes (calls `init_store` at `serve` start).

## API contract

Internal — no API surface beyond T12's endpoint, which this task mounts.

## Acceptance criteria

### AC-18 — happy

> **Given** the integration runs in dry-run mode
> **When** the integration operator replays deliveries
> **Then** every unit of work gets the outcome it would have, including the customer and order it would create, and nothing is written to the accounting system
>
> — `spec.md §5, AC-18, verbatim` · full text: [spec.md](../spec.md)

AC-17 (the owner's manual two-replay run) becomes runnable with this task; it is verified by the owner, not by a test.

## Checklist

- [ ] `load_config(env) -> Config` (frozen dataclass); missing → error listing names only; `DRY_RUN` true unless exactly `false` — `app/config.py`
- [ ] `main(argv)`: `serve` (init store, build clients, `create_app(...)` with `process_delivery`, `uvicorn.run(..., workers=1)`), `replay`, `report`; no command still returns 0 — `app/__main__.py`
- [ ] Tests: missing vars → message has names, not values; `DRY_RUN` unset → true; unknown command → exit 2 — `tests/test_config.py`, `tests/test_main.py`

## Edge cases

| Case | Behaviour |
|---|---|
| `DRY_RUN=False` / `0` / empty | assumption: only `false` (case-insensitive, trimmed) turns writes on; anything else keeps dry run (safe default) |
| `.env` file | never read by tests; tests pass an explicit env dict |

## Definition of Done

- [ ] Tests above pass; smoke test unchanged and green
- [ ] No secret value in any error message or log
- [ ] `ruff check . && pytest` green
- [ ] The exact manual commands for AC-17 are printed in the handoff for the human (rule 7); the agent does not run them
