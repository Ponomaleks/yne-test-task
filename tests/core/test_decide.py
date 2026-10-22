import pytest

from app.core.decide import Decision, decide_customer, decide_deal

WON = {("p1", "s1")}
GOOD = [{"orgnr": "123456789", "country": "Norway"}]
ITEMS = [{"id": "li1"}]


def decide(**overrides):
    args = {
        "pipeline_id": "p1",
        "stage_id": "s1",
        "won": WON,
        "companies": GOOD,
        "line_items": ITEMS,
        "currency": "NOK",
    }
    args.update(overrides)
    return decide_deal(**args)


def test_orderable_carries_normalized_orgnr():
    result = decide(companies=[{"orgnr": "NO 123456789 MVA", "country": "Norge"}])
    assert result == Decision("orderable", "", "123456789")


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"stage_id": "other"}, "current stage not won"),
        ({"companies": []}, "no company"),
        ({"companies": GOOD * 2}, "several companies"),
        ({"companies": [{"orgnr": "SE556677889901", "country": "Norway"}]}, "foreign customer"),
        ({"companies": [{"orgnr": "123456789", "country": "Sweden"}]}, "foreign customer"),
        ({"companies": [{"orgnr": None, "country": "Norway"}]}, "missing or invalid orgnr"),
        ({"companies": [{"orgnr": "12345", "country": "Norway"}]}, "missing or invalid orgnr"),
        ({"line_items": []}, "no line items"),
        ({"currency": None}, "no currency"),
        ({"currency": ""}, "no currency"),
    ],
)
def test_reasons(overrides, reason):
    result = decide(**overrides)
    assert result.reason == reason
    assert result.outcome == ("skipped" if reason == "current stage not won" else "held")
    assert result.orgnr is None


def test_foreign_takes_precedence_over_invalid_orgnr():
    result = decide(companies=[{"orgnr": "SE12", "country": None}])
    assert result.reason == "foreign customer"


def test_not_won_is_checked_before_missing_company():
    result = decide(stage_id="other", companies=[])
    assert result.outcome == "skipped"
    assert result.reason == "current stage not won"


def test_several_customers_are_held():
    result = decide_customer([{"id": "c1"}, {"id": "c2"}])
    assert result.outcome == "held"
    assert result.reason == "orgnr matches several customers"


@pytest.mark.parametrize("matches", [[], [{"id": "c1"}]])
def test_zero_or_one_customer_is_orderable(matches):
    assert decide_customer(matches).outcome == "orderable"
