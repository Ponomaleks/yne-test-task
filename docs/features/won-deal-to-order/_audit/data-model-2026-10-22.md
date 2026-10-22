# Audit — data-model won-deal-to-order (2026-10-22)

## Staged migrations

Staged, not yet in the live schema. `implement` promotes them.

| Ordinal | Up | Down |
|---|---|---|
| 01 | `docs/features/won-deal-to-order/migrations/01_create_deliveries.up.sql` | `01_create_deliveries.down.sql` |
| 02 | `docs/features/won-deal-to-order/migrations/02_create_events.up.sql` | `02_create_events.down.sql` |
| 03 | `docs/features/won-deal-to-order/migrations/03_create_outcomes.up.sql` | `03_create_outcomes.down.sql` |
| 04 | `docs/features/won-deal-to-order/migrations/04_create_rejections.up.sql` | `04_create_rejections.down.sql` |

## Promote-time convention hint

The repo has no migration tool and no `migrations/` tree (architecture map §Migrations, ADR-0003).
Promotion means appending the `.up.sql` bodies, in ordinal order, to `app/schema.sql`, which
`init_store` applies at startup. No sequence numbers are needed. The `.down.sql` files are kept for
reversibility and review only. In this repo a rollback means deleting the local SQLite file.

## Self-check (4 mandatory)

| Check | Result |
|---|---|
| Naming follows the repo | Pass: snake_case plural tables, `CREATE ... IF NOT EXISTS`, as in `app/schema.sql` |
| Down reversibility | Pass: each CREATE TABLE and CREATE INDEX has a DROP; applied in memory up, up, then down in reverse, and the store ended with 0 objects |
| FK indexes | Pass: `outcomes.event_id` → `idx_outcomes_event_id`. The query plan for the last-outcome read uses the index |
| Convention adherence | Pass: the owner confirmed the greenfield choices on 2026-10-22 (append-only outcomes, CHECKs, INTEGER PRIMARY KEY for local rows, INTEGER epoch ms timestamps). Run in memory: a CHECK rejected an unknown outcome and `dry_run = 2`; the FK rejected an unknown event; `INSERT OR IGNORE` kept one row for a repeated event |

ER diagram: no `mmdc` available. The structural lint passed (valid `||--o{` glyph, `type name [PK|FK]`
attribute lines).

## Drift

No domain layer exists yet (scaffold only: `app/store.py`, `app/schema.sql`), so there is nothing to
compare. No `_drift/` files.

## Breaking changes

None. All tables are new. The existing schema contains only `PRAGMA user_version = 1`.

## Open points (TBD for implement)

- `PRAGMA foreign_keys = ON` must be set on every short-lived connection in `app/store.py`, or the FK
  is not enforced.
- `PRAGMA user_version` stays at 1. `tests/test_store.py` asserts 1, so bumping it would change a
  test; leave it unless the owner decides otherwise.
- Resolved (owner, 2026-10-22): an event that fails body validation is logged and counted in the
  delivery summary, not stored. sad.md §8 Validation row updated to match. All recorded deliveries
  parse and carry an `eventId` (`evidence/api-hubspot-webhooks.md`), so this path is a safeguard.
