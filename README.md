# won-deal-to-order

When a deal is won in HubSpot, this integration finds or creates the customer in PowerOffice and
creates one Draft sales order with the deal's line items, discounts and currency. Finance reviews
the Draft before invoicing; the integration never sends an invoice. Deals that cannot be matched
safely are held for review with a reason instead of being guessed.

> **Timing note.** The on-time submission (deadline 2026-10-23 00:30) decided every event correctly
> but could not create orders in PowerOffice. The cause was found and fixed after the
> deadline, in a separate pull request. See [After the deadline](#after-the-deadline). The history
> keeps both states.

## Status

| Area | Status |
|---|---|
| Webhook endpoint with signature check (v3) | Verified against the test system: 10 deliveries accepted, 1 forged delivery rejected |
| Won check in any pipeline, from the current deal state | Verified against the test system |
| Customer lookup by normalized orgnr, create when missing | Verified against the test system (after the deadline): 2 existing customers reused, 1 created once and reused for a second deal |
| Draft order with lines, discount and currency | Verified against the test system (after the deadline): 4 orders, discount carried over |
| Non-NOK currency (deal currency passed as `currencyCode`) | Verified by a manual order in the test system: EUR accepted and kept, amount not converted |
| Hold rules | Missing and foreign orgnr verified against the test system; several companies or customers, deal not found, no lines or currency, total mismatch tested with mocks only |
| Idempotency (duplicate events, lookup by external key before create) | Verified against the test system (after the deadline): a second replay created nothing |
| Write failure handling (no blind POST retry) | Verified against the test system (after the deadline): an order created behind a 502 was found by reference, no duplicate |
| 429 handling, timeouts | Tested with mocks only |
| Dry run | Verified against the test system |
| `replay` command | Verified against the test system |
| `report` command | Not built (cut for time); outcomes are in the `serve` log and the store |

### Result of the recorded deliveries

| Deal | Outcome | Details |
|---|---|---|
| 40211700201 | ordered | new customer; the delivery arrives twice, one order |
| 40211700202 | ordered | existing customer; PowerOffice answers 502 but creates the order, the next replay records "order already exists" |
| 40211700203 | ordered | existing customer, orgnr written as "NO ... MVA"; discount 4000 per unit becomes 14.29 %, rounding noted |
| 40211700206 | ordered | reuses the customer created for 201; the later amount event is recorded as "change after order, not handled" |
| 40211700204 | held | missing or invalid orgnr |
| 40211700205 | held | foreign customer (German company, EUR) |
| 40211700207 | skipped | current stage not won (the last event says won, the deal does not) |
| 40211700208 | skipped | current stage not won (lost) |
| 40211700210 | skipped | current stage not won (new deal) |
| 40211700209 | rejected | the delivery's signature does not match: a forged webhook for a deal that does not exist |

A second full replay created no customer and no order: every event was a duplicate or found its
order by reference.

## How it works

1. The endpoint verifies the HubSpot signature over the raw body, stores the events and answers 204
   right away.
2. A background task processes each event: it reads the deal's **current** state from HubSpot,
   decides with pure rules, and records exactly one outcome: `ordered`, `skipped`, `held` or `failed`.
3. Before any write, it checks that the line items add up to the deal amount, then looks up by
   external key: the order by reference `hubspot-deal-<dealId>` (exact match), the customer by
   normalized orgnr.
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

Terminal 1, the webhook service on `http://127.0.0.1:8000` (localhost only). It logs one line per
processed event and one summary line per delivery:

```bash
python -m app serve
```

Terminal 2, replay the recorded deliveries to `http://127.0.0.1:8000/webhooks/hubspot`:

```bash
python -m app replay
```

Processing runs in the background, paced for the HubSpot rate limit; it takes about 30 seconds.
To read the stored outcomes afterwards:

```bash
python -c "import sqlite3;c=sqlite3.connect('data/store.db');cur=c.execute('select event_id,deal_id,outcome,reason,dry_run from outcomes order by id');[print(r) for r in cur]"
```

`DRY_RUN=true` is the default: every decision is made and recorded, nothing is written to
PowerOffice. Set `DRY_RUN=false` in `.env`, reload it and restart `serve` for a real run.

To start over: stop `serve`, delete `data/store.db`, call the PowerOffice test reset
(`POST /_testverktoy/tilbakestill`), then start `serve` again. The tables are created at startup,
so delete the store only while `serve` is stopped.

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

## After the deadline

The live run at the deadline showed `failed: AccountingError` for every order, with no detail. The
follow-up pull request found and fixed three things, each recorded in
[docs/FINDINGS.md](docs/FINDINGS.md):

1. **Error detail.** PowerOffice errors are now logged with status, error code and field names
   (never values). This showed the real cause on the next run.
2. **Field name.** The task docs show the line price as `unitPrice`; the test system requires
   `unitPriceExVat`. Our code and our mocks both followed the docs.
3. **Write that fails but succeeds.** PowerOffice answered 502 for deal 202 but created the order.
   No code change was needed: the client does not retry a POST, and the next replay found the order
   by reference.
4. **Lost discount.** HubSpot returns the line item `discount` only when it is requested in
   `properties`. The client did not request it, so deal 203's order was created without its discount
   (84 000 instead of 72 000). Fixed by requesting it, plus a guard that holds a deal when the line
   items do not add up to the deal amount.

All four orderable deals now have exactly one correct Draft order, verified in PowerOffice.

## Project layout

```
app/
  core/        pure rules: signature, orgnr, won check, hold rules, total check, order mapping
  clients/     HubSpot and PowerOffice HTTP clients (timeouts, 429 handling, error detail)
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
- **Operations:** alerting on held and failed events, a dead-letter view, and a simple way for
  finance to resolve held deals.
- **Verification of writes:** compare the order PowerOffice returns with the expected total, and
  agree with finance how to handle the rounding of percentage discounts (deal 203: 71 996,40
  instead of 72 000).

## Known limitations

- From the spec, section 3: no automatic scheduled retries, no timestamp age check, no paging of deal
  associations, no NFR measurement or alerting, foreign customers are held rather than handled, no
  name-based matching, and changes after an order is created are recorded but not applied.
- Cut for time: the `report` command. Outcomes are in the `serve` log and the store.
- `.env` is not loaded by the app; load it into the shell as shown.
- The HubSpot client retries a 429 without a cap (it always waits for the limit window).
- No test asserts that the order sent to PowerOffice is a Draft; the live orders were all Draft.
- `pydantic` is used directly but comes in through FastAPI; it is not listed in `pyproject.toml`.
