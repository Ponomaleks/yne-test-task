from decimal import Decimal

import pytest

from app.core.order import build_order, discount_percent, external_key


def test_external_key():
    assert external_key("123") == "hubspot-deal-123"


def test_discount_percent_exact():
    assert discount_percent(Decimal("200"), Decimal("50")) == (Decimal("25.00"), False)


def test_discount_percent_rounded():
    assert discount_percent(Decimal("300"), Decimal("100")) == (Decimal("33.33"), True)


def test_discount_percent_rounds_half_up():
    # 1 / 8 = 12.5 exactly; 1 / 16 = 6.25 exactly; 1 / 32 = 3.125 -> 3.13
    assert discount_percent(Decimal("32"), Decimal("1")) == (Decimal("3.13"), True)


def test_discount_percent_null_is_zero():
    assert discount_percent(Decimal("300"), None) == (Decimal("0.00"), False)


def test_discount_percent_zero_price_raises():
    with pytest.raises(ValueError):
        discount_percent(Decimal("0"), Decimal("5"))


def test_build_order_one_line_per_item_in_order():
    items = [
        {"name": "Alpha", "price": "300", "quantity": "2", "discount": "100"},
        {"name": "Beta", "price": "10.50", "quantity": "1", "discount": None},
    ]
    order, rounded = build_order("42", "EUR", items, "cust-1")

    assert rounded is True
    assert order["customerId"] == "cust-1"
    assert order["currencyCode"] == "EUR"
    assert order["reference"] == "hubspot-deal-42"
    assert [line["description"] for line in order["lines"]] == ["Alpha", "Beta"]
    assert order["lines"][0] == {
        "description": "Alpha",
        "quantity": Decimal("2"),
        "unitPrice": Decimal("300"),
        "discountPercent": Decimal("33.33"),
    }
    assert order["lines"][1]["unitPrice"] == Decimal("10.50")
    assert order["lines"][1]["discountPercent"] == Decimal("0.00")


def test_build_order_not_rounded_and_no_status_or_invoice_field():
    items = [{"name": "A", "price": "200", "quantity": "1", "discount": "50"}]
    order, rounded = build_order("1", "NOK", items, "c")

    assert rounded is False
    assert set(order) == {"customerId", "reference", "currencyCode", "lines"}
    assert all(isinstance(v, Decimal) for k, v in order["lines"][0].items() if k != "description")
