"""Decide whether a deal is skipped, held for review, or orderable. Pure rules, no I/O."""

from dataclasses import dataclass
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


def decide_customer(matches: list) -> Decision:
    if len(matches) > 1:
        return _held("orgnr matches several customers")
    return Decision("orderable")
