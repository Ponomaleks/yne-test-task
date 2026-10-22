---
status: Living
updated_at: "2026-10-22"
---

# Domain Context — won-deal-to-order

## Glossary

- Company — the organization a deal belongs to in the CRM, with an orgnr, invoice email and country. NOT a customer: a company lives in the CRM, a customer lives in the accounting system.
- CRM — HubSpot, where sales representatives manage deals. NOT the accounting system.
- Accounting system — PowerOffice, where finance keeps customers and sales orders and invoices from them. NOT the CRM.
- Customer — the accounting-system record an order is attached to, identified by its orgnr. NOT a company (the CRM record it is matched from).
- Deal — a sales opportunity in the CRM with an amount, a currency, a stage, one or more companies and line items. NOT an order.
- Delivery — one recorded webhook request from the CRM, holding one or more events and a signature. NOT an event: one delivery can carry several events.
- Event — one change notification inside a delivery, identified by its event ID and naming one deal. NOT the deal's current state, which can differ from the event's value.
- External key — the deal-based reference written on an order and searched before any create, so a deal never gets two orders. NOT the order's own ID in the accounting system.
- Finance reviewer — a person in the finance department who reviews Draft orders before invoicing and resolves held deals. NOT the integration operator.
- Held for review — outcome of a unit of work that the integration must not decide automatically; it keeps a reason and stays persisted for the finance reviewer; it is not re-decided automatically in this slice. NOT skipped (nothing to do) and NOT failed (a technical error).
- Integration operator — the person who starts the integration, replays deliveries, which retries failed units of work. NOT a finance reviewer.
- Line item — one product line on a deal with price, quantity and an optional discount in currency per unit. NOT an order line, which carries the discount as a percentage.
- orgnr — the Norwegian organization number: exactly 9 digits after removing spaces, an optional "NO" prefix and an optional "MVA" suffix. NOT a foreign registration number, even if it has 9 digits after another prefix.
- Sales order — the Draft order in the accounting system that finance invoices from. NOT an invoice; the integration never sends one.
- Sales representative — a person who moves deals through the pipeline in the CRM. NOT an actor of the integration itself.
- Skipped — outcome of a unit of work that needs no action (the deal is not won, or its order already exists), with a reason. NOT held for review.
- Unit of work — the processing of one event for one deal, ending in exactly one outcome: ordered, skipped, held for review or failed. NOT a delivery.
- Won stage — a pipeline stage that is closed with probability 1.0, in any pipeline. NOT only the stage named "closedwon".

## Invariants

- A deal can never have more than one sales order created by the integration.
- Every event in a delivery always ends in exactly one recorded outcome with a reason; nothing is dropped silently.
- The integration can never send an invoice.
- A foreign registration number is never turned into an orgnr by stripping its prefix.
