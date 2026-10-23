"""Process one event: read the current deal, decide, look up, create, record one outcome.

Outcomes carry technical IDs, statuses and reasons only, never personal values.
"""

import logging
import threading
import time
from dataclasses import dataclass

from app.clients.hubspot import DealNotFound, HubSpotError
from app.clients.poweroffice import AccountingError
from app.core.decide import decide_customer, decide_deal
from app.core.order import build_order, external_key
from app.core.won import won_stages
from app.store import has_final_outcome, record_outcome

log = logging.getLogger(__name__)

# One process-wide lock: two deliveries of the same deal must not both find no order.
_delivery_lock = threading.Lock()


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
    except AccountingError as exc:
        # Kept as failed so the next replay retries it.
        result = Outcome("failed", _accounting_reason(exc))
    except HubSpotError as exc:
        result = Outcome("failed", type(exc).__name__)
    record_outcome(
        store_path, event["event_id"], deal_id, result.outcome, result.reason, result.dry_run
    )
    log.info(
        "event processed event_id=%s deal_id=%s outcome=%s reason=%s",
        event["event_id"],
        deal_id,
        result.outcome,
        result.reason,
    )
    return result


def _accounting_reason(exc: AccountingError) -> str:
    """Status, error code and field names when the system answered; the type name otherwise."""
    if exc.status is None:
        return type(exc).__name__
    fields = ",".join(exc.fields)
    return f"failed: {type(exc).__name__} {exc.status} {exc.error_code} fields={fields}"


def process_delivery(
    delivery_id: str, events: list[dict], *, hubspot, poweroffice, store_path, dry_run: bool
) -> dict[str, int]:
    """Process the events of one delivery under the lock; return counts per outcome and duplicates.

    Bind the keyword arguments with functools.partial to get the web callback
    shape `process(delivery_id, events)`.
    """
    started = time.monotonic()
    counts: dict[str, int] = {}
    with _delivery_lock:
        for event in events:
            if has_final_outcome(store_path, event["event_id"]):
                key = "duplicate"
            else:
                key = _process_isolated(event, hubspot, poweroffice, store_path, dry_run)
            counts[key] = counts.get(key, 0) + 1
    log.info(
        "delivery=%s events=%d ordered=%d skipped=%d held=%d failed=%d duplicate=%d duration_ms=%d",
        delivery_id,
        len(events),
        counts.get("ordered", 0),
        counts.get("skipped", 0),
        counts.get("held", 0),
        counts.get("failed", 0),
        counts.get("duplicate", 0),
        (time.monotonic() - started) * 1000,
    )
    return counts


def _process_isolated(event: dict, hubspot, poweroffice, store_path, dry_run: bool) -> str:
    """One event never stops the others: an unexpected error is recorded as failed."""
    try:
        return process_event(
            event, hubspot=hubspot, poweroffice=poweroffice, store_path=store_path, dry_run=dry_run
        ).outcome
    except Exception as exc:
        reason = f"failed: {type(exc).__name__}"
        deal_id = str(event["deal_id"])
        record_outcome(store_path, event["event_id"], deal_id, "failed", reason, False)
        log.error("event failed event_id=%s error=%s", event["event_id"], reason)
        return "failed"


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
