# won-deal-to-order

When a deal is won in HubSpot, this integration finds or creates the customer in PowerOffice and
creates one Draft sales order with the deal's line items, discounts and currency. Finance reviews
the Draft before invoicing; the integration never sends an invoice. Deals that cannot be matched
safely are held for review with a reason instead of being guessed.

## Status

| Area | Status |
|---|---|
| Webhook endpoint with signature check (v3) | Verified against the test system: 10 deliveries accepted, 1 forged delivery rejected |
| Won check in any pipeline, from the current deal state | Verified against the test system (dry run) |
| Customer lookup by normalized orgnr | Verified against the test system (dry run): existing customers found for 2 deals |
| Customer and Draft order create | Tested with mocks only. In the live run PowerOffice rejected the creates (see below) |
| Hold rules (missing or foreign orgnr, several companies or customers, deal not found, no lines or currency) | Missing and foreign orgnr verified against the test system; the others tested with mocks only |
| Idempotency (duplicate events, lookup by external key before create) | Tested with mocks only; in the dry run the repeated delivery of deal 201 was handled as expected |
| Non-NOK currency (deal currency passed as `currencyCode`) | Verified by a manual order in the test system |
| 429 handling, timeouts, no blind retry of writes | Tested with mocks only |
| Dry run | Verified against the test system |
| `replay` command | Verified against the test system |
| `report` command | Not built (cut for time); outcomes are read from the store, see below |

### Result of the recorded deliveries

| Deal | Outcome | Reason |
|---|---|---|
| 40211700201 | ordered | new customer; delivered twice, one order |
| 40211700202 | ordered | existing customer |
| 40211700203 | ordered | existing customer, orgnr written as "NO ... MVA" |
| 40211700206 | ordered | reuses the customer created for 201; the later amount event is recorded as "change after order, not handled" |
| 40211700204 | held | missing or invalid orgnr |
| 40211700205 | held | foreign customer (German company, EUR) |
| 40211700207 | skipped | current stage not won (the last event says won, the deal does not) |
| 40211700208 | skipped | current stage not won (lost) |
| 40211700210 | skipped | current stage not won (new deal) |
| 40211700209 | rejected | the delivery's signature does not match: a forged webhook for a deal that does not exist |

**Dry run** (`DRY_RUN=true`): matches the table above.

**Live run** (`DRY_RUN=false`): the skipped, held and rejected outcomes match the table. For the
four orderable deals, every call that writes to PowerOffice ended in `failed: AccountingError`.
The failure handling worked as designed: the service kept running, every accepted event got an
outcome, and the failed events stay stored, so the next replay retries them after a lookup by
external key. The cause was not found within the time box: the app records only the error type,
never the error body, so the next step is to log the PowerOffice error code and field names
(no values) and replay.

## How it works

1. The endpoint verifies the HubSpot signature over the raw body, stores the events and answers 204
   right away.
2. A background task processes each event: it reads the deal's **current** state from HubSpot,
   decides with pure rules, and records exactly one outcome: `ordered`, `skipped`, `held` or `failed`.
3. Before any create, it looks up by external key: the customer by normalized orgnr, the order by
   reference `hubspot-deal-<dealId>` (exact match).
4. A failed event is retried by replaying the deliveries again. Duplicates are safe.

The recorded webhooks cannot reach this service directly, so the `replay` command fetches them from
the HubSpot test tool and posts them byte for byte, with their original headers, to the local
endpoint. The signature is checked against the original webhook address (`HUBSPOT_WEBHOOK_URI`).

## Run it

Requirements: Python 3.12 or newer (developed on 3.14). Commands below are for Git Bash.

```bash
python -m venv .venv
source .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
python -m pip install -e .[dev]
cp .env.example .env                 # then fill in the keys from the task page
mkdir -p data                        # the SQLite store lives in data/store.db
```

The app reads its settings from the environment, not from the `.env` file itself, so load `.env`
into each terminal first:

```bash
set -a; . ./.env; set +a
```

Terminal 1, the webhook service on `http://127.0.0.1:8000` (localhost only):

```bash
python -m app serve
```

Terminal 2, replay the recorded deliveries to `http://127.0.0.1:8000/webhooks/hubspot`:

```bash
python -m app replay
```

Processing runs in the background after each delivery, paced for the HubSpot rate limit, so wait
about a minute, then read the outcomes from the store:

```bash
python -c "import sqlite3;c=sqlite3.connect('data/store.db');cur=c.execute('select * from outcomes order by 1');print([d[0] for d in cur.description]);[print(r) for r in cur]"
```

`DRY_RUN=true` is the default: every decision is made and recorded, nothing is written to
PowerOffice. Set `DRY_RUN=false` in `.env`, reload it and restart `serve` for a real run. To start
over, call the PowerOffice test reset and delete `data/store.db`.

### Webhook endpoint

`POST /webhooks/hubspot`, authenticated by the HubSpot v3 signature only.

| Response | When |
|---|---|
| 204 | The delivery is accepted and its events are stored; processing runs after the response |
| 400 | The signature is valid, but the body cannot be parsed |
| 401 | The signature is missing or does not match |
| 500 | The delivery could not be stored; HubSpot retries the delivery later, so nothing is lost |

The path mirrors the original webhook address. It is not versioned, because HubSpot fixes the
request shape. Contracts: [openapi.yaml and cli.md](docs/features/won-deal-to-order/contracts/).

## Tests

```bash
ruff check . && pytest
```

The check is hermetic: no network, no containers. HTTP clients are faked with `httpx.MockTransport`,
the endpoint is tested in-process with FastAPI's `TestClient`, and the decision rules are pure
functions tested directly. CI runs the same check on every push.

## Project layout

```
app/
  core/        pure rules: signature, orgnr, won check, hold rules, order mapping
  clients/     HubSpot and PowerOffice HTTP clients (timeouts, 429 handling)
  web.py       webhook endpoint
  processor.py one unit of work per event, and one delivery under a lock
  store.py     SQLite store, schema applied at startup
  replay.py    replay of recorded deliveries
  config.py    settings from the environment, validated once
tests/
docs/
```

## Documentation

- [Spec](docs/features/won-deal-to-order/spec.md): user stories, acceptance criteria, scope and known limitations
- [Architecture](docs/features/won-deal-to-order/sad.md): design, flows, risks
- [ADRs](docs/adr/): stack, structure, storage; [ADR-0004](docs/features/won-deal-to-order/adr/): processing and retry
- [Findings](docs/FINDINGS.md): where the test systems differ from the docs or from expectations
- [API evidence](evidence/): response shapes captured from the test systems, no personal data
- [AI workflow](docs/AI_WORKFLOW.md): how the AI agents were steered, and where I stepped in

## What production would need

- **Storage and queue:** PostgreSQL and a managed queue with an outbox, instead of one SQLite file and
  an in-process background task, so several instances can run and retries are scheduled and durable.
- **Security:** a public HTTPS endpoint, the 5-minute timestamp check, secrets in a vault.
- **Operations:** structured logging and alerting on held and failed events, a dead-letter view, and
  a simple way for finance to resolve held deals.

## Known limitations

- From the spec, section 3: no automatic scheduled retries, no timestamp age check, no paging of deal
  associations, no NFR measurement or alerting, foreign customers are held rather than handled, no
  name-based matching, and changes after an order is created are recorded but not applied.
- Cut for time: the `report` command, and application INFO logging (only HTTP access lines are
  printed). Outcomes are read from the store with the query above.
- `.env` is not loaded by the app; load it into the shell as shown.
- The HubSpot client retries a 429 without a cap (it always waits for the limit window).
- No test asserts that the order sent to PowerOffice is a Draft; new orders are Draft by default in
  PowerOffice.
- `pydantic` is used directly but comes in through FastAPI; it is not listed in `pyproject.toml`.
