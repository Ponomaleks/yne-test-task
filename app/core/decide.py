"""Decide whether a deal is skipped, held for review, or orderable. Pure rules, no I/O."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from app.core.orgnr import is_foreign, normalize_orgnr
from app.core.won import is_won


@dataclass(frozen=True)
class Decision:
    outcome: Literal["skipped", "held", "orderable"]
    reason: str = ""
    orgnr: str | None = None


def _held(reason: str) -> Decision:
    return Decision("held", reason)


def decide_deal(
    pipeline_id: str,
    stage_id: str,
    won: set[tuple[str, str]],
    companies: list[dict],
    line_items: list,
    currency: str | None,
) -> Decision:
    """Apply the rules in spec order; each company dict has "orgnr" and "country"."""
    if not is_won(pipeline_id, stage_id, won):
        return Decision("skipped", "current stage not won")
    if not companies:
        return _held("no company")
    if len(companies) > 1:
        return _held("several companies")
    company = companies[0]
    # Foreign is checked before validity so a foreign prefix is never stripped to nine digits.
    if is_foreign(company.get("orgnr"), company.get("country")):
        return _held("foreign customer")
    orgnr = normalize_orgnr(company.get("orgnr"))
    if orgnr is None:
        return _held("missing or invalid orgnr")
    if not line_items:
        return _held("no line items")
    if not currency:
        return _held("no currency")
    return Decision("orderable", orgnr=orgnr)


def decide_total(amount: str | None, line_items: list[dict]) -> Decision:
    """Hold the deal unless its line items add up to the deal amount.

    The discount is currency per unit, as in the order mapping, so a line totals
    quantity x (price - discount); a missing discount is 0. A missing or unreadable
    amount cannot be checked, so it is held too.
    """
    total = Decimal(0)
    for item in line_items:
        discount = Decimal(item.get("discount") or 0)
        total += Decimal(item["quantity"]) * (Decimal(item["price"]) - discount)
    try:
        matches = amount is not None and Decimal(amount) == total
    except InvalidOperation:
        matches = False
    return Decision("orderable") if matches else _held("order total does not match deal amount")


def decide_customer(matches: list) -> Decision:
    if len(matches) > 1:
        return _held("orgnr matches several customers")
    return Decision("orderable")
