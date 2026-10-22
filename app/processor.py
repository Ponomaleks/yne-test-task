"""Process one event: read the current deal, decide, look up, create, record one outcome.

Outcomes carry technical IDs, statuses and reasons only, never personal values.
"""

import logging
from dataclasses import dataclass

from app.clients.hubspot import DealNotFound, HubSpotError
from app.clients.poweroffice import AccountingError
from app.core.decide import decide_customer, decide_deal
from app.core.order import build_order, external_key
from app.core.won import won_stages
from app.store import record_outcome

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Outcome:
    outcome: str
    reason: str
    dry_run: bool = False


def process_event(event: dict, *, hubspot, poweroffice, store_path, dry_run: bool) -> Outcome:
    """Run one unit of work and record its outcome; never raises for a per-event failure."""
    deal_id = str(event["deal_id"])
    try:
        result = _decide_and_act(event, deal_id, hubspot, poweroffice, dry_run)
    except DealNotFound:
        result = Outcome("held", "deal not found")
    except (HubSpotError, AccountingError) as exc:
        # Kept as failed so the next replay retries it.
        result = Outcome("failed", type(exc).__name__)
    record_outcome(
        store_path, event["event_id"], deal_id, result.outcome, result.reason, result.dry_run
    )
    log.info(
        "event processed",
        extra={"event_id": event["event_id"], "deal_id": deal_id, "outcome": result.outcome},
    )
    return result


def _decide_and_act(event: dict, deal_id: str, hubspot, poweroffice, dry_run: bool) -> Outcome:
    # The current deal is read; the event's own property value is never trusted.
    deal = hubspot.get_deal(deal_id)
    won = won_stages(hubspot.get_pipelines()["results"])
    companies = [hubspot.get_company(cid) for cid in deal.company_ids]
    items = [hubspot.get_line_item(lid) for lid in deal.line_item_ids]
    currency = deal.properties.get("deal_currency_code")

    decision = decide_deal(
        deal.properties.get("pipeline"),
        deal.properties.get("dealstage"),
        won,
        [{"orgnr": c.properties.orgnr, "country": c.properties.country} for c in companies],
        items,
        currency,
    )
    if decision.outcome != "orderable":
        return Outcome(decision.outcome, decision.reason)

    key = external_key(deal_id)
    if poweroffice.find_orders(key):
        reason = (
            "change after order, not handled"
            if event.get("property_name") == "amount"
            else "order already exists"
        )
        return Outcome("skipped", reason)

    matches = poweroffice.find_customers(decision.orgnr)
    customer_decision = decide_customer(matches)
    if customer_decision.outcome != "orderable":
        return Outcome(customer_decision.outcome, customer_decision.reason)

    line_items = [i.properties.model_dump() for i in items]
    if dry_run:
        # Build with a placeholder customer so mapping errors surface in a dry run too.
        build_order(deal_id, currency, line_items, "dry-run")
        customer = f"existing customer {matches[0]['id']}" if matches else "would create customer"
        return Outcome("ordered", f"{customer}, would create order {key}", dry_run=True)

    if matches:
        customer_id = matches[0]["id"]
    else:
        company = companies[0].properties
        # Only Norwegian companies reach this point (foreign ones are held).
        customer_id = poweroffice.create_customer(
            company.name, decision.orgnr, company.fakturaepost, "NO"
        )
    order, rounded = build_order(deal_id, currency, line_items, customer_id)
    order_id = poweroffice.create_order(order)
    reason = f"order {order_id}" + ("; discount rounded" if rounded else "")
    return Outcome("ordered", reason)
