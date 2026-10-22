"""Pure mapping of a won deal and its line items to a Draft sales order payload."""

from decimal import ROUND_HALF_UP, Decimal

_TWO_PLACES = Decimal("0.01")


def external_key(deal_id: str) -> str:
    return f"hubspot-deal-{deal_id}"


def discount_percent(unit_price: Decimal, discount: Decimal | None) -> tuple[Decimal, bool]:
    """Return (percent, rounded). The CRM states discount as currency per unit."""
    if discount is None:
        return Decimal("0.00"), False
    if unit_price == 0:
        raise ValueError("cannot express a discount as a percentage of a zero unit price")
    exact = discount * 100 / unit_price
    percent = exact.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
    return percent, percent != exact


def build_order(
    deal_id: str, currency: str, line_items: list[dict], customer_id: str
) -> tuple[dict, bool]:
    """Build the POST /v2/SalesOrders body; the second value says any discount was rounded."""
    lines = []
    any_rounded = False
    for item in line_items:
        unit_price = Decimal(item["price"])
        raw_discount = item.get("discount")
        discount = Decimal(raw_discount) if raw_discount is not None else None
        percent, rounded = discount_percent(unit_price, discount)
        any_rounded = any_rounded or rounded
        lines.append(
            {
                "description": item["name"],
                "quantity": Decimal(item["quantity"]),
                "unitPrice": unit_price,
                "discountPercent": percent,
            }
        )
    order = {
        "customerId": customer_id,
        "reference": external_key(deal_id),
        "currencyCode": currency,
        "lines": lines,
    }
    return order, any_rounded
