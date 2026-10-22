---
id: T3
title: "Verify the HubSpot v3 signature in a pure function"
layer: "domain"
deps: []
blocks: ["T12"]
acs: ["AC-15"]
files_hint: ["app/core/signature.py", "tests/core/test_signature.py"]
owner: "Oleksandr Ponomarenko"
estimate: "S"
context_budget: "S"
status: "todo"
step: ""
---

# T3 — Verify the HubSpot v3 signature in a pure function

## Place in the sequence

- **Blocked by:** — · **Blocks:** T12 — Webhook endpoint · **Wave:** 1, pure, no inputs.
- **Lane:** own lane.

## Why (user story)

> **As an** Integration operator
> **I want** deliveries whose signature does not prove they came from the CRM to be rejected
> **So that** nobody can create orders by sending forged deliveries
>
> — `spec.md §4, US-05, verbatim` · full text: [spec.md](../spec.md)

This task delivers the check itself: build the signed text and compare in constant time.

## Inlined context

> Inbound authentication — Signature v3: HMAC over method, `HUBSPOT_WEBHOOK_URI`, raw body and
> timestamp, compared in constant time. Never the local URL. Timestamp age check waived (spec §6.1).
>
> — `sad.md §8, Inbound authentication, verbatim` · full text: [sad.md](../sad.md)

> HMAC-SHA256 signature v3 made by the CRM with the app secret (`HUBSPOT_WEBHOOKS_SECRET`) over
> method + `HUBSPOT_WEBHOOK_URI` + raw body + `X-HubSpot-Request-Timestamp`.
>
> — `contracts/openapi.yaml, securitySchemes HubSpotSignatureV3, abridged` · full text: [openapi.yaml](../contracts/openapi.yaml)

The signed text is concatenated with no separators, and the HMAC digest is base64-encoded
(`docs/interview-reference/task/yne-api-uk.md`, section on webhooks, abridged — git-ignored task doc).

`app/core/` is pure: no I/O, no env reads (ADR-0002). Secret, URI, method, body bytes and timestamp are arguments.

**Fallback:** insufficient → read [sad.md](../sad.md) §8 and [ADR-0002](../../../adr/0002-separate-pure-core-from-io-edges.md). Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface (T12 calls it for `POST /webhooks/hubspot`).

## Acceptance criteria

### AC-15 — authorization

> **Given** a delivery whose signature is missing or does not match the delivery content
> **When** the integration receives it
> **Then** the delivery is rejected, none of its events are processed, and the rejection is recorded with the delivery's technical identity only
>
> — `spec.md §5, AC-15, verbatim` · full text: [spec.md](../spec.md)

## Checklist

- [ ] `signed_text(method, uri, body: bytes, timestamp: str) -> bytes` — `app/core/signature.py`
- [ ] `is_valid_signature(secret, method, uri, body, timestamp, signature: str | None) -> bool` using `hmac.compare_digest` — `app/core/signature.py`
- [ ] Tests with a synthetic secret: a signature computed in the test passes; a changed body, changed URI, changed timestamp, missing signature each fail — `tests/core/test_signature.py` (create empty `tests/core/__init__.py` if missing)

## Edge cases

| Case | Behaviour |
|---|---|
| Signature `None` or empty | `False`, no exception |
| Timestamp `None` | `False` (cannot match) |
| Body differs by one byte (e.g. reformatted JSON) | `False` — the raw bytes are signed |

## Definition of Done

- [ ] Unit tests above pass
- [ ] No I/O or env access in `app/core/signature.py`
- [ ] `ruff check . && pytest` green
