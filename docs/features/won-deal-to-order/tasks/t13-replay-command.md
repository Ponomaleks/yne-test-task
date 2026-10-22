---
id: T13
title: "Replay recorded deliveries byte for byte to the local endpoint"
layer: "ports"
deps: ["T8"]
blocks: ["T15"]
acs: ["AC-17", "AC-19"]
files_hint: ["app/replay.py", "tests/test_replay.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "S"
status: "done"
step: "COMMIT"
---

# T13 — Replay recorded deliveries byte for byte to the local endpoint

## Place in the sequence

- **Blocked by:** T8 — HubSpot client · **Blocks:** T15 — Config and CLI wiring · **Wave:** 2.
- **Lane:** own lane.

## Why (user story)

> **As an** Integration operator
> **I want** to retry failed units of work by replaying the recorded deliveries, with held and failed units of work kept persisted
> **So that** a temporary error does not need manual re-keying and nothing is lost between runs
>
> — `spec.md §4, US-09, verbatim` · full text: [spec.md](../spec.md)

This task is the replay (and therefore the retry): fetch the recorded deliveries, post each unchanged.

## Inlined context

> The `replay` CLI fetches the recorded deliveries from the CRM test tool and posts each one byte for byte, with its original headers, to the local endpoint, in order. Only the human runs it.
>
> — `adr/0004, Decision outcome, verbatim` · full text: [ADR-0004](../adr/0004-process-events-in-a-background-task-and-retry-by-replay.md)

> `replay` — Posts every recorded delivery, in order and unchanged, to `http://127.0.0.1:8000/webhooks/hubspot`; also the retry (AC-19). Exit `1` when the CRM fetch fails or the service is unreachable.
> CLI prints counts of posted, acknowledged and rejected deliveries.
>
> — `contracts/cli.md, Commands, replay + sad.md §6 Flow 1 last step, abridged` · full text: [cli.md](../contracts/cli.md)

Recorded delivery shape: `results[]` with `leveranse` (number), `method`, `uri`, `headers` (`Content-Type`, `X-HubSpot-Signature-v3`, `X-HubSpot-Request-Timestamp`), `body` (string) — `evidence/api-hubspot-webhooks.md §Response shape, abridged`.
Body must be sent as `body.encode("utf-8")` exactly; never re-serialize JSON.

**Fallback:** insufficient → read [cli.md](../contracts/cli.md) and ADR-0004. Do not guess.

## Data delta

No DB changes.

## API contract

Calls `POST http://127.0.0.1:8000/webhooks/hubspot` (T12) with the recorded headers; `204` counts as acknowledged, `401` as rejected — `contracts/openapi.yaml, receiveDelivery, abridged`.

## Acceptance criteria

### AC-17 — happy

> **Given** the recorded deliveries of the test CRM
> **When** the integration operator replays them all, and then replays them all a second time
> **Then** the first replay creates orders for deals 40211700201, 40211700202, 40211700203 and 40211700206 (one each, although 40211700201 is delivered twice), holds 40211700204, 40211700205 and 40211700209, and skips 40211700207, 40211700208 and 40211700210; the second replay creates no customer and no order. The table matches the accounting-system probes (§1 traceability): no orgnr in it matches several existing customers, so AC-09 turns none of these orders into holds
>
> — `spec.md §5, AC-17, verbatim` · full text: [spec.md](../spec.md)

### AC-19 — happy

> **Given** persisted units of work from an earlier run, some failed for a technical reason and some held for review
> **When** the integration operator replays the recorded deliveries again (there is no separate retry action in this slice)
> **Then** each failed unit of work is decided again from the deal's current state and ends in a new recorded outcome without a duplicate customer or order (AC-12, AC-13); held units of work keep their outcome and reason and stay persisted for the finance reviewer
>
> — `spec.md §5, AC-19, verbatim` · full text: [spec.md](../spec.md)

AC-17 itself is the owner's manual run; this task's tests cover only the byte-for-byte posting.

## Checklist

- [ ] `replay(hubspot, http: httpx.Client, target_url) -> dict` counts `posted`, `acknowledged`, `rejected`, posting in `results` order with original headers and raw body bytes — `app/replay.py`
- [ ] Tests: a fake HubSpot returning two synthetic deliveries and a MockTransport target capturing requests: bytes and headers equal the recorded ones, order kept; a 401 counts as rejected — `tests/test_replay.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Target unreachable | raise; T15 maps to exit `1` |
| Body with non-ASCII characters | posted as UTF-8 bytes, unchanged |

## Definition of Done

- [ ] Tests above pass; no real network
- [ ] `ruff check . && pytest` green
