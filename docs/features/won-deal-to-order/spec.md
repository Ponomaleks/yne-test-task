---
status: Draft
owner: "Oleksandr Ponomarenko"
reviewers: ["Tech Lead", "Security Lead"]
updated_at: "2026-10-22"
feature_size: "S"
---

# Spec — won-deal-to-order

> **Glossary:** [CONTEXT](./CONTEXT.md)
> **Inputs used:** [idea brief](../../idea-brief.md) (§1–§8); task text and API docs in `docs/interview-reference/task/` (git-ignored, not quoted); evidence `evidence/api-hubspot-webhooks.md`, `evidence/api-hubspot-pipelines.md`, `evidence/api-hubspot-deal.md`, `evidence/api-hubspot-deals-summary.md`, `evidence/api-hubspot-deals-summary-2.md`; [FINDINGS](../../FINDINGS.md).

## 1. Context

Fjordforum's sales representatives manage deals in the CRM (HubSpot); finance invoices from the
accounting system (PowerOffice). Today a person re-keys every won deal by hand, which creates
customers twice, loses discounts and sends invoices to the wrong company (task text; brief §2).
Finance reviewers need every won deal to arrive as exactly one Draft sales order on the right
customer, and to see clearly which deals the integration could not decide (brief §3).

Trigger: a time-boxed assignment of 4 hours, started 2026-10-22 20:30 local time, that values a
small working, tested part over everything half done (brief §4).

Committed approach (brief §7, owner-accepted): the CRM's recorded webhook deliveries are replayed
into a local integration. For each event it reads the deal's current state from the CRM, decides
won or not from the pipeline configuration, matches or creates the customer by orgnr, and creates
one Draft sales order with the deal's line items and currency. Every event ends in a recorded
outcome: ordered, skipped, held for review, or failed; held and failed units of work stay
persisted, and failed ones are retried by replaying the recorded deliveries. Handling later amount or stage changes on an existing order is a
stretch slice (feature 2) and is otherwise answered in writing.

Traceability:
- Owner rules from the evidence round (2026-10-22, this session): won = closed stage with
  probability 1.0 in any pipeline, resolved from the pipeline configuration; orgnr normalization
  and the foreign-customer rule; "deal not found" is held and not retried automatically; the order
  carries the deal currency; the expected outcome table in AC-17; the multi-company rule is tested
  with a synthetic case because no recorded deal has several companies.
- Evidence facts: HubSpot rate limit 20 requests per 10 000 ms, `Retry-After` not observed
  (FINDINGS); the deal ID is text in the CRM but a number in events (`evidence/api-hubspot-deal.md`,
  `evidence/api-hubspot-webhooks.md`); line items carry no currency of their own, the deal does
  (`evidence/api-hubspot-deals-summary.md`).
- Owner decisions from the spec ledger (2026-10-22): an event is a duplicate only when it already has
  a final outcome; exactly one order per deal comes from the lookup by external key; a retry is a
  replay of the recorded deliveries; the discount becomes a percentage rounded to two decimals, with
  the rounding noted. Netting the discount into the unit price was rejected because the discount
  would disappear from the order line.
- Accounting-system evidence (`evidence/api-poweroffice.md`, 2026-10-22): the token works and
  expires after 900 s, so fetching a new token after an authentication rejection is enough for a
  run; customer and order searches return a plain list; company 21894400101 has no customer yet,
  21894400102 and 21894400103 each match exactly one existing customer by the normalized orgnr,
  and no orgnr matches several customers; no order exists yet for deal 40211700201.
- Not yet verified: exact versus partial matching of the order search by external key (§8, open
  until the first live run); discount precision and the error format, which the probes did not
  exercise.

## 2. Goals

- Every won deal that can be decided safely becomes exactly one Draft sales order on the right
  customer, with its line items, discounts and currency.
- No duplicates: repeated deliveries, repeated events, replays and retries never create a second
  customer or a second order.
- Nothing is lost or decided silently: every event has a recorded outcome with a reason, held
  and failed units of work stay persisted, and failed ones are retried by a replay.

## 3. Non-goals

- Updating or cancelling an order after a later amount or stage change — the accounting system
  documents no update or delete for orders; feature 2 may only flag such changes (brief §5).
- Matching customers by name — risks duplicates and the wrong company (brief §5, Q2).
- Sending invoices — forbidden by the task; finance invoices after review.
- Deployment, a user interface and production hardening — not required; answered in writing
  (brief §5).
- Re-deciding held units of work — finance resolves them; not in this slice (owner, critic round).

### Slice 1 scope (owner, 2026-10-22)

Implement: the signature check; persisted events with a fast success acknowledgement; processing
from the current deal state; won in any pipeline; one outcome per event; all hold rules as pure
functions (AC-06 to AC-11, AC-22); lookup before create for customer and order; Draft only; the
deal currency; the discount as a percentage; minimal request-limit handling (wait for the
interval, retry); dry run. AC-17 is the manual acceptance check, run by the owner.

### Known limitations (documented only, not implemented)

- Automatic scheduled retries — a retry is a manual replay of the recorded deliveries.
- Feature 2 flagging beyond the outcome reason "change after order, not handled".
- The delivery timestamp age check.
- Token refresh beyond fetching a new token after an authentication rejection.
- Paging of deal associations.
- Measurement of the §6 NFR targets.
- Alerting.
- A production queue and database.
- Foreign customer handling beyond holding for review.
- Matching customers by name.

## 4. User stories

### US-01: Won deal becomes Draft order

**As a** Finance reviewer
**I want** each won deal to appear as one Draft sales order with the deal's line items, discounts and currency
**So that** I can review and invoice it without re-keying anything

### US-02: Reuse the right customer

**As a** Finance reviewer
**I want** the order attached to the existing customer with the same orgnr, or to a new customer only when none exists
**So that** customers are never created twice and invoices reach the right company

### US-03: Hold deals that need a human

**As a** Finance reviewer
**I want** deals the integration cannot match safely to be held for review with a plain reason
**So that** no order is attached to a guessed customer

### US-04: Survive repeats and failures

**As an** Integration operator
**I want** repeated deliveries, repeated events and failures of the CRM or the accounting system to never create a second order or lose an event
**So that** I can replay and retry without fear

### US-05: Accept only genuine deliveries

**As an** Integration operator
**I want** deliveries whose signature does not prove they came from the CRM to be rejected
**So that** nobody can create orders by sending forged deliveries

### US-06: Account for every event

**As an** Integration operator
**I want** every event to end in exactly one recorded outcome with a reason, and a summary per run
**So that** I can see what was ordered, skipped, held or failed

### US-07: Any won pipeline counts

**As a** Sales representative
**I want** a deal marked won in any pipeline to be picked up
**So that** I do not need extra steps for deals outside the default pipeline

### US-08: Rehearse without writing

**As an** Integration operator
**I want** a dry run that decides every outcome but writes nothing to the accounting system
**So that** I can check the result before the real run

### US-09: Retry by replaying

**As an** Integration operator
**I want** to retry failed units of work by replaying the recorded deliveries, with held and failed units of work kept persisted
**So that** a temporary error does not need manual re-keying and nothing is lost between runs

## 5. Acceptance criteria

### AC-01 (US-01) — happy

**Given** a deal whose current stage is a won stage, with one company that has a valid orgnr matching exactly one existing customer, and at least one line item
**When** the integration processes an event for that deal
**Then** the accounting system holds one Draft sales order for that customer with one order line per line item (description, quantity, unit price, discount), the deal's currency and the deal's external key, and the unit of work is recorded as ordered

### AC-02 (US-02) — happy

**Given** a won deal whose company has a valid orgnr that matches no existing customer
**When** the integration processes the event
**Then** a new customer is created with the company's name, orgnr, invoice email and country, and the Draft sales order is attached to that new customer

### AC-03 (US-02) — cross-context

**Given** a customer already exists for a company's orgnr, created earlier for another deal
**When** a second won deal for the same company is processed
**Then** the order is attached to the existing customer and no new customer is created

### AC-04 (US-01) — cross-context

**Given** an event says a deal moved to a won stage, but the deal's current stage in the CRM is not a won stage
**When** the integration processes the event
**Then** no order is created and the unit of work is recorded as skipped with the reason "current stage not won"

### AC-05 (US-07) — cross-context

**Given** a deal whose current stage is closed with probability 1.0 in a pipeline other than the default one
**When** the integration processes an event for that deal
**Then** the deal is treated as won, exactly as a deal in the default pipeline's won stage

### AC-06 (US-03) — domain invariant

**Given** a company orgnr written as nine digits, as digits with spaces, or with a "NO" prefix, an "MVA" suffix, or both
**When** the integration reads the company
**Then** it uses the nine digits as the orgnr, and any other result than exactly nine digits is treated as an invalid orgnr

### AC-07 (US-03) — error

**Given** a won deal whose company has no orgnr, or an orgnr that is not nine digits after normalization
**When** the integration processes the event
**Then** no customer and no order are created, and the deal is held for review with the reason "missing or invalid orgnr"

### AC-08 (US-03) — domain invariant

**Given** a won deal whose company has a foreign registration prefix other than "NO", or a country other than Norway
**When** the integration processes the event
**Then** the prefix is never stripped to produce nine digits, no customer or order is created, and the deal is held for review with the reason "foreign customer"; this reason takes precedence over "missing or invalid orgnr" (AC-07)

### AC-09 (US-03) — domain invariant

**Given** a won deal whose valid orgnr matches more than one existing customer
**When** the integration processes the event
**Then** no order is created and the deal is held for review with the reason "orgnr matches several customers"

### AC-10 (US-03) — domain invariant

**Given** a won deal with more than one company, or with no company
**When** the integration processes the event
**Then** no order is created and the deal is held for review with the reason "several companies" or "no company"

### AC-11 (US-03) — error

**Given** an event names a deal that the CRM reports as not existing
**When** the integration processes the event
**Then** the unit of work is held for review with the reason "deal not found" and is not retried automatically

### AC-12 (US-04) — domain invariant

**Given** an event that already has a final outcome (ordered, skipped or held for review), or a won event for a deal that already has its Draft sales order
**When** that event arrives again, or the other won event is processed
**Then** the event with a final outcome keeps that outcome as its only recorded outcome, and the run summary counts it as "duplicate event"; the won event for a deal with an order creates no second order and is recorded as skipped with the reason "order already exists", found by the deal's external key (AC-13), not by the event ID; an event whose last outcome is failed is not a duplicate and is processed again; an amount event for a deal that already has its order gets the reason "change after order, not handled" instead (AC-16)

### AC-13 (US-04) — error

**Given** the accounting system fails or does not answer while an order is being created
**When** the integration handles that failure
**Then** the unit of work is recorded as failed with the reason and stays persisted, and a retry first checks for an existing order with the deal's external key and creates one only if none is found

### AC-14 (US-04) — error

**Given** the CRM reports that its request limit is reached
**When** the integration is reading deals, companies or line items
**Then** it waits for the limit window and continues, and no event is lost or marked failed because of the limit alone

### AC-15 (US-05) — authorization

**Given** a delivery whose signature is missing or does not match the delivery content
**When** the integration receives it
**Then** the delivery is rejected, none of its events are processed, and the rejection is recorded with the delivery's technical identity only

### AC-16 (US-06) — happy

**Given** a delivery with several events, where one event is a lost deal, one is a new deal in an early stage, one is an amount change on a deal that already has an order, and one fails
**When** the integration processes the delivery
**Then** each event gets its own outcome with a reason ("current stage not won", "current stage not won", "change after order, not handled", "failed: <reason>"), and the failing event does not stop the other events

### AC-17 (US-06) — happy

**Given** the recorded deliveries of the test CRM
**When** the integration operator replays them all, and then replays them all a second time
**Then** the first replay creates orders for deals 40211700201, 40211700202, 40211700203 and 40211700206 (one each, although 40211700201 is delivered twice), holds 40211700204 and 40211700205, skips 40211700207, 40211700208 and 40211700210, and rejects one delivery (deal 40211700209) with 401 `delivery.signature_mismatch` (AC-15); the second replay creates no customer and no order. Deal 40211700209 is not held for "deal not found": its only delivery fails the signature check, so nothing from it is stored or processed (docs/FINDINGS.md, 2026-10-23). AC-11 stays as a rule, covered by tests with mocks only. The table matches the accounting-system probes (§1 traceability): no orgnr in it matches several existing customers, so AC-09 turns none of these orders into holds

### AC-18 (US-08) — happy

**Given** the integration runs in dry-run mode
**When** the integration operator replays deliveries
**Then** every unit of work gets the outcome it would have, including the customer and order it would create, and nothing is written to the accounting system

### AC-19 (US-09) — happy

**Given** persisted units of work from an earlier run, some failed for a technical reason and some held for review
**When** the integration operator replays the recorded deliveries again (there is no separate retry action in this slice)
**Then** each failed unit of work is decided again from the deal's current state and ends in a new recorded outcome without a duplicate customer or order (AC-12, AC-13); held units of work keep their outcome and reason and stay persisted for the finance reviewer

### AC-20 (US-01) — domain invariant

**Given** any won deal processed by the integration
**When** its order is created
**Then** the order stays a Draft for finance review and no invoice is ever sent

### AC-21 (US-01) — domain invariant

**Given** a line item with a discount stated in currency per unit
**When** its order line is created
**Then** the discount is carried over as a percentage of the unit price and is never dropped; if the percentage cannot represent the discount exactly, the line uses the nearest percentage with two decimals and the outcome notes the rounding

### AC-22 (US-01) — error

**Given** a won deal with no line items, or with no currency
**When** the integration processes the event
**Then** no order is created and the deal is held for review with the reason "no line items" or "no currency"

## 6. Non-functional requirements

| Aspect | Target | Measurement |
|---|---|---|
| Delivery acknowledgement time | ≤ 5 s per delivery (the CRM retries after 5 s), target p95 ≤ 1 s | duration logged per delivery |
| Duplicate orders or customers | 0 across two consecutive full replays | replay summary plus order lookup by external key |
| Events without a recorded outcome | 0 per replay | event count in deliveries equals outcome count |
| CRM request rate | ≤ 20 requests per 10 000 ms, per the rate-limit headers | request log; count of limit responses that end in a lost event = 0 |
| Timeout per external call | ≤ 15 s | client configuration, test with a stalled fake |

## 6.1 Security / privacy

- **Data classification:** confidential — customer company data and invoice emails of a real business process.
- **Personal data touched:** company name, invoice email, city and country (read from the CRM, written to the accounting system); deal name and the CRM user reference in events (read only). None of these appear in logs, outcomes, fixtures or documents; outcomes carry technical IDs, counts, statuses and reasons only.
- **AuthZ/AuthN impact:** inbound deliveries are accepted only with a valid signature made with the app secret over the request method, the original delivery address, the raw content and the timestamp; outbound access uses the app token for the CRM and client credentials for the accounting system, all from configuration, never in code or logs.
- **Abuse cases:**
  - Forged delivery: rejected, no processing (AC-15).
  - Replayed genuine delivery: accepted (the timestamp age check is waived for the recorded test deliveries, per the docs), but deduplicated by event ID and external key, so no second order (AC-12).
  - Data leak through logs: outcomes and logs hold technical IDs and reasons only.
  - Request flood toward the CRM: requests are paced to the published rate limit (AC-14).
- **Security review:** Required — a new inbound surface that triggers writes to a finance system; covered in `/sdd:review`.

## 7. Metrics / KPIs

- **Orderable won deals with exactly one Draft order** — baseline: 0 (manual re-keying), target: 4 of 4 in the recorded replay, on the first replay.
- **Duplicates created by a second replay** — baseline: not measured, target: 0 customers and 0 orders.
- **Events without a recorded outcome** — baseline: not measured, target: 0 per replay, counting events in accepted deliveries; events in rejected deliveries are never stored (AC-15).
- **Held deals with a plain reason** — baseline: 0, target: 2 of 2 in the recorded replay (deal 40211700209 is rejected by the signature check, not held; see AC-17).

## 8. Open questions

- [ ] Does the order search by external key match exactly, or also partially? Default now: treat a found order as a match only when its reference equals the deal's external key exactly. — owner: Oleksandr Ponomarenko, due: first live run (AC-17)