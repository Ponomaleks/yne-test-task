---
status: Draft
owner: "Oleksandr Ponomarenko"
updated_at: "2026-10-22"
feature_size: "S"
---

# CLI contract — won-deal-to-order

> Derived from [sad.md](../sad.md) §4, §5, §7, §8 and [ADR-0004](../adr/0004-process-events-in-a-background-task-and-retry-by-replay.md).
> Endpoint: [openapi.yaml](./openapi.yaml). Origins and drift: [api-sync-report.md](./api-sync-report.md).

Entry point: `python -m app <command>` (argparse). No command has options: every setting comes from
the environment, validated once by `app/config.py` (sad.md §8 Configuration).

## Exit codes (all commands)

| Code | Meaning |
|---|---|
| `0` | Finished. Rejected deliveries and failed events are counted, not an exit failure |
| `1` | Blocking failure: missing configuration (variable names only), authentication rejected, system unreachable, store not readable |
| `2` | Usage error (argparse default) |

## Commands

| Command | Options | Does | Exit `1` when |
|---|---|---|---|
| `serve` | none | Runs the webhook service on `127.0.0.1:8000`, one uvicorn worker (sad.md §7, ADR-0004) | configuration is invalid at startup |
| `replay` | none | Posts every recorded delivery, in order and unchanged, to `http://127.0.0.1:8000/webhooks/hubspot`; also the retry (AC-19) | the CRM fetch fails or the service is unreachable |
| `report` | none | Prints the run summary from the store (sad.md §8 Run summary) | the store cannot be opened |
