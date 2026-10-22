---
status: Draft
owner: "Oleksandr Ponomarenko"
updated_at: "2026-10-22"
depth: "medium"
---

# Idea brief — won-deal-to-order

## 1. Raw idea

> I have opened the task and placed the task text into the `docs\interview-reference\task` folder.

The task text itself lives in `docs/interview-reference/task/` (git-ignored, personal use only; not
quoted here). Owner's first interview answer, verbatim:

> Won only for the first slice: customer plus Draft order, idempotent. Every other event is not dropped
> silently: it is recorded as skipped with a reason. Flagging amount or stage changes on deals that
> already have an order is a planned stretch slice (feature 2), only if the first slice is green and
> pushed. Questions 1 and 2 are answered in writing either way.

## 2. Problem

Fjordforum's sales team works in HubSpot (CRM); finance invoices from PowerOffice. Today someone
re-keys every won deal into PowerOffice by hand. The task names three resulting errors: customers
created twice, discounts lost, and invoices sent to the wrong company (source: task text, git-ignored).

Desired observable outcome: when a HubSpot deal becomes won, PowerOffice holds exactly one Draft
sales order for it, with the deal's line items and discounts, attached to the right customer.
Finance reviews the draft before invoicing; the integration never sends an invoice (task text).
No deal is ordered twice, and nothing is lost when an API errors or does not answer (task text).

Proposed solution (not the problem): a local service that receives HubSpot webhooks, finds or
creates the customer in PowerOffice and creates the Draft order. Recorded webhook deliveries are
replayed from the HubSpot test system into this service (task text; API docs §"Test tool").

## 3. Users

- Finance department: reviews Draft orders and invoices from them; acts on deals held for review.
  (task text; their review step is owner-reported as the safety net, no further user research.)
- Sales team: marks deals as won in HubSpot; no change to their workflow (task text).
- Operator of the integration (in this assignment: the owner): starts the service, replays
  deliveries, retries held or failed units of work. (owner-reported)
- Assessor of the assignment: reads the commit history, README and written explanation (task text).

## 4. Why now

Time-boxed assignment of 4 hours, started 2026-10-22 (owner-reported). The task explicitly expects
prioritization: a small part that works and is tested over everything half done (task text).

## 5. Out of scope

- Updating or cancelling an existing order when the deal amount or stage changes later
  (owner-accepted, Q1). PowerOffice docs list no update or delete for SalesOrders (source-verified,
  API docs §PowerOffice "Orders"). Feature 2 (stretch, only after slice 1 is green and pushed) may
  *flag* such changes. Task questions 1 and 2 are answered in writing either way.
- Name-based customer matching (owner-accepted, Q2). Customers without a valid Norwegian orgnr
  are held for review; foreign customers are answered in writing (task question 3).
- Sending invoices (task text: forbidden).
- Deployment and a user interface (task text: not required; runs locally).
- Production hardening; answered in writing (task question 4).

Constraints to preserve:
- Every event that is not processed is recorded as skipped with a reason, never dropped silently
  (owner-accepted, Q1).
- orgnr normalization before any decision: strip spaces, an "NO" prefix and an "MVA" suffix, then
  require exactly 9 digits (owner-accepted, Q2).
- Hold for review, with the reason kept and retry possible (superseded 2026-10-22 by the spec ledger: held units are not re-decided automatically in slice 1), when the orgnr is missing or invalid,
  or when a valid orgnr matches more than one existing PowerOffice customer (owner-accepted, Q2),
  or when the won deal has more than one associated company (owner-accepted, Q3).
- Language, framework and tools are free; queue and store may be simple (SQLite or a file), with
  a written note on what production would use (task text).
- API keys never in the repo (task text; CLAUDE.md).

## 6. Risks

Weakest assumption first. Critique was inline (no independent helper), given the time box.

1. **The test systems differ from the docs.** The task warns they behave like the real systems,
   "including in ways the docs do not describe". Every field, filter and status below is
   doc-sourced until `evidence/` confirms it. Reversible: findings go to `docs/FINDINGS.md`.
2. **Duplicate orders on a lost response.** A create that times out may still have succeeded.
   The lookup before create depends on PowerOffice search behaving as documented (exact vs
   contains match on the order reference is not stated).
3. **Concurrent or repeated deliveries for one deal.** HubSpot delivers at least once, and one
   delivery can hold several events; two units of work for the same deal could race.
4. **Discount unit mismatch.** HubSpot `discount` is an amount in NOK per unit; PowerOffice takes
   `discountPercent`. Converting can lose precision, the exact error the task names.
5. **Signature verification.** HubSpot signs method + original URI + raw body + timestamp; the
   original URI is the Fjordforum address, not the local endpoint. Verifying against the wrong URI
   or a re-serialized body rejects every delivery.
6. **Personal data.** Company names, invoice emails and deal names are customer data and must
   not reach logs, fixtures or docs (CLAUDE.md).

Evidence ledger:

| Claim / question | Class | Source | Finding / limit |
|---|---|---|---|
| Webhook events: `deal.creation`, `deal.propertyChange` on `dealstage`, `amount`; at-least-once; retry if no 2xx within 5 s | source-verified (docs only) | docs/interview-reference/task/yne-api-uk.md §"Вебхуки", read 2026-10-22 | Test behavior not yet observed |
| Signature: HMAC-SHA256 over method+uri+body+timestamp, base64; timestamp age can be ignored | source-verified (docs only) | same file, §"Вебхуки" | Not yet verified against a recorded delivery |
| PowerOffice SalesOrders: GET by reference / customerId / id, POST; no update or delete listed | source-verified (docs only) | same file, §"Замовлення" | Absence in docs is not proof of absence |
| Customers: search by organizationNumber or name contains; POST requires `name` | source-verified (docs only) | same file, §"Клієнти" | Multiple matches per orgnr possible (owner decision covers it) |
| Order `reference` is free text up to 50 chars and searchable | source-verified (docs only) | same file, §"Замовлення" | Match semantics not stated |
| HubSpot `discount` is NOK per unit; PowerOffice line uses `discountPercent` | source-verified (docs only) | same file, §"Об'єкти", §"Замовлення" | Rounding rule undecided |
| All HubSpot property values are strings; empty fields are `null` | source-verified (docs only) | same file, §"Об'єкти" | — |
| Finance review is the safety net for wrong data on Draft orders | owner-reported | task text | — |
| No API response shapes captured yet | source-verified | `evidence/` does not exist (checked 2026-10-22) | Blocks specify (owner decision, Q3) |

## 7. Recommendation

Direction (owner-accepted, Q3): slice 1 turns a won HubSpot deal into exactly one Draft sales order
in PowerOffice, attached to the right customer under the agreed orgnr and company rules (§5). Every
other event is recorded as skipped with a reason. Held and failed units of work stay persisted and
can be retried. The decision uses the deal's current state fetched from HubSpot, not the value in the
event, because events can arrive repeated or out of order (proposed by the interviewer, accepted by
the owner in Q3).

Owner changes in Q3: a won deal with more than one associated company is held for review; API
evidence is required before `/sdd:specify`, not only before design.

Observable result: replaying the recorded deliveries yields one Draft order per won deal, no
duplicate customers or orders on a second replay, and a recorded reason for every skipped or held
event.

Major tradeoff: holding deals for review (no orgnr, ambiguous match, several companies) protects
against wrong-company invoices and duplicates, at the cost of manual work for finance.

Rejected alternatives: name-based customer matching and always creating new customers (Q2:
duplicate and wrong-company risk, the task's named problems); handling amount or stage changes in
code in slice 1 (Q1: no documented update or delete; planned as the flagging stretch, feature 2).

Outcome: needs-evidence

Update 2026-10-22: the HubSpot evidence blockers in §8 are resolved by `evidence/api-hubspot-*.md`
(owner); specify proceeded on that basis. Superseded by the spec ledger: held units of work are not
re-decided automatically in slice 1; only failed ones are retried, by a replay.

Next action: the owner captures API shapes with `/explore-api` into `evidence/`, covering the open
points in §8, then runs `/sdd:specify won-deal-to-order`.

## 8. Open questions

| Question | Consequence | Blocking? | Verification action | Owner |
|---|---|---|---|---|
| Do the real API shapes match the docs (deal, company, line item, customer search, order create, error format)? | Field names, filters and statuses in the spec may be wrong | Resolved for HubSpot 2026-10-22 (`evidence/api-hubspot-*.md`); PowerOffice shapes still open, before design (owner) | `/explore-api` per system, save shapes to `evidence/` | Oleksandr Ponomarenko |
| How is "won" identified: only `closedwon`, or any stage with `isClosed` true and probability 1.0 in any pipeline? | Wrong deals ordered, or won deals missed | Resolved 2026-10-22: any stage with `isClosed` "true" and probability 1.0 (`evidence/api-hubspot-pipelines.md`, FINDINGS) | Inspect `GET /crm/v3/pipelines/deals` via `/explore-api` | Oleksandr Ponomarenko |
| Which orgnr formats occur in the real company data? | The normalization rule may reject valid numbers or accept invalid ones | Resolved 2026-10-22: 9 digits, digits with spaces, "NO ... MVA", foreign prefix seen (`evidence/api-hubspot-deals-summary*.md`) | Observe formats (shape only, no values) via `/explore-api` | Oleksandr Ponomarenko |
| Which scenarios do the recorded webhook deliveries contain (event types, repeats, several events per delivery, deals leaving won)? | Spec could miss a scenario the replay exercises | Resolved 2026-10-22 (`evidence/api-hubspot-webhooks.md`) | Inspect `GET /_testverktoy/webhooks` via `/explore-api` | Oleksandr Ponomarenko |
| Does the order reference search match exactly or by "contains"? | Lookup before create could hit the wrong order | Nonblocking for specify | Observe in evidence | Oleksandr Ponomarenko |
| Discount conversion: rounding rule for NOK-per-unit to percent, and what to do if the order total then differs | Lost or wrong discounts | Nonblocking; decide in specify | Owner decision in specify | Oleksandr Ponomarenko |
