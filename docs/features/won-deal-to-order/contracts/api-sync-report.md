# API sync report — won-deal-to-order

> Contracts: [openapi.yaml](./openapi.yaml) (webhook endpoint), [cli.md](./cli.md) (`serve`,
> `replay`, `report`). Surfaces from sad.md frontmatter `target_surfaces: [backend-service, cli]`.
> No `events.md`: processing is an in-process background task, with no message bus and no
> published events (ADR-0004). Size S, route quick.

## A. Field origins

| schema_path | origin | confidence |
|---|---|---|
| receiveDelivery.header.X-HubSpot-Signature-v3 | spec.md §6.1; sad.md §8 Inbound authentication; evidence header names | high |
| receiveDelivery.header.X-HubSpot-Request-Timestamp | data-model.md → deliveries.request_timestamp (INTEGER), rejections.request_timestamp (TEXT, NULL) | high |
| receiveDelivery.body (Delivery array size) | data-model.md → deliveries.event_count (≥ 0) | high |
| Event.eventId | data-model.md → events.event_id (INTEGER PK) | high |
| Event.objectId | data-model.md → events.deal_id (TEXT; integer in events, sad.md §8 IDs) | high |
| Event.subscriptionType | data-model.md → events.subscription_type (TEXT NOT NULL) | high |
| Event.propertyName | data-model.md → events.property_name (TEXT NULL) | high |
| Event.additionalProperties | evidence `api-hubspot-webhooks.md` event fields; ignored, not stored (spec.md §6.1) | high |
| Error.code `delivery.signature_missing` / `delivery.signature_mismatch` | data-model.md → rejections.reason ("signature missing" / "signature mismatch"); flow 4 alt | high |
| Error.code `delivery.invalid_body` | derived: valid signature, body not an event array (no flow 4 branch) | medium |
| Error.code `delivery.not_persisted` | derived: store write fails before the ack (no flow 4 branch) | medium |
| cli.report line `event/deal/outcome/reason` | data-model.md → outcomes.event_id, deal_id, outcome, reason; sad.md §8 Run summary | high |
| cli.serve / replay address `127.0.0.1:8000` | owner decision 2026-10-22 (sad.md §7 "bound to localhost") | medium |

## B. Drift checklist

1. **Endpoint ↔ data-model** ✓ — `receiveDelivery` writes `deliveries`, `events`, `rejections`;
   `report` reads `outcomes`.
2. **Error code ↔ repo error definition** ✓ — no error registry found in `app/` (skeleton only);
   the four `delivery.*` codes are the contract's proposal. Reconcile when the code defines them.
3. **Validation ↔ constraint** ✓ — `eventId`/`objectId` integer, `propertyName` nullable, timestamp
   header digits (INTEGER column), `Error.code` enum.
4. **OpenAPI ↔ sequence** ✓ with two accepted gaps — flow 4: signature missing/mismatch → 401,
   valid → 204 before processing. 400 and 500 have no flow 4 branch.

## C. Flags and resolutions (owner, 2026-10-22)

| # | Flag | Resolution |
|---|---|---|
| 1 | Inbound auth is signature v3 (`HubSpotSignatureV3`), not the default global BearerAuth | Accepted: sourced from spec.md §6.1, sad.md §8. No ADR |
| 2 | Path `/webhooks/hubspot`, no `/api/v1` URL versioning | Accepted: mirrors the recorded delivery address (evidence); the CRM fixes the request shape. No ADR |
| 3 | 400 `delivery.invalid_body`: no flow 4 branch | Accepted as is; kept in the contract |
| 4 | 500 `delivery.not_persisted`: no flow 4 branch | Accepted as is; kept in the contract |
| 5 | sad.md said `report` prints one line per deal; a deal can have several events | Fixed: one line per event; sad.md §5, §7, §8 Run summary and §12 Report reworded in this stage |
| 6 | No source fixed the local address | Fixed: constant `127.0.0.1:8000`, no option, no env variable |

Other decisions, low risk and reversible: acknowledgement is `204 No Content` (any 2xx satisfies the
CRM; no response field has an origin). A missing or non-digit timestamp header is rejected as
`signature_mismatch`, since `rejections.reason` has only two values. No `Idempotency-Key`: the CRM
sends none, and the event ID is the key (AC-12).

Coverage back-feed: US-04, US-05, US-06 → `receiveDelivery`; US-04, US-06, US-09 → `replay`,
`report`; US-01–03, US-07, US-08 are processing outcomes with no interface of their own (read via
`report`). AC-15 → 401, AC-12 → 204 on repeats, AC-16/AC-17/AC-19 → `replay` + `report`. No
missing AC found.

Lint: `spectral lint` not wired (it would be a new dependency; ask first). Not run.
