import threading
from functools import partial

import pytest

from app.clients.hubspot import Company, Deal, DealNotFound, HubSpotError, LineItem
from app.clients.poweroffice import AccountingError
from app.processor import process_delivery, process_event
from app.store import init_store, last_outcome, save_events

PIPELINES = {
    "results": [
        {
            "id": "p1",
            "stages": [
                {"id": "won", "metadata": {"isClosed": "true", "probability": "1.0"}},
                {"id": "open", "metadata": {"isClosed": "false", "probability": "0.5"}},
            ],
        }
    ]
}
COMPANY_NAME = "Secret Name AS"


class FakeHubSpot:
    # amount 180 = quantity 2 x (price 100.00 - discount 10) of the one line item below.
    def __init__(
        self, stage="won", orgnr="123456785", missing=False, read_error=False, amount="180"
    ):
        self.stage = stage
        self.orgnr = orgnr
        self.missing = missing
        self.read_error = read_error
        self.amount = amount

    def get_deal(self, deal_id):
        if self.missing:
            raise DealNotFound("404")
        if self.read_error:
            raise HubSpotError("CRM unreachable")
        return Deal(
            id=deal_id,
            properties={
                "dealstage": self.stage,
                "pipeline": "p1",
                "deal_currency_code": "NOK",
                "amount": self.amount,
            },
            associations={
                "companies": {"results": [{"id": "c1"}]},
                "line_items": {"results": [{"id": "l1"}]},
            },
        )

    def get_pipelines(self):
        return PIPELINES

    def get_company(self, company_id):
        return Company(
            id=company_id,
            properties={
                "name": COMPANY_NAME,
                "orgnr": self.orgnr,
                "country": "Norway",
                "fakturaepost": "a@example.invalid",
            },
        )

    def get_line_item(self, line_item_id):
        return LineItem(
            id=line_item_id,
            properties={"name": "Item", "price": "100.00", "quantity": "2", "discount": "10"},
        )


class FakePowerOffice:
    def __init__(self, customers=(), orders=(), fail_order=False):
        self.customers = list(customers)
        self.orders = list(orders)
        self.fail_order = fail_order
        self.posts = []
        self.customer_lookups = 0

    def find_customers(self, orgnr):
        self.customer_lookups += 1
        return self.customers

    def find_orders(self, reference):
        return self.orders

    def create_customer(self, name, orgnr, email, country_code):
        self.posts.append(("customer", name, orgnr, email, country_code))
        return "cust-new"

    def create_order(self, payload):
        self.posts.append(("order", payload))
        if self.fail_order:
            raise AccountingError("POST /v2/SalesOrders failed: ReadTimeout")
        return "order-1"


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "t.db"
    init_store(path)
    return path


def event(store, subscription_type="deal.propertyChange", property_name="dealstage"):
    e = {
        "event_id": 1,
        "deal_id": 42,
        "subscription_type": subscription_type,
        "property_name": property_name,
    }
    save_events(store, [e])
    return e


def run(store, hubspot, po, dry_run=False, **event_kwargs):
    return process_event(
        event(store, **event_kwargs),
        hubspot=hubspot,
        poweroffice=po,
        store_path=store,
        dry_run=dry_run,
    )


def test_ac01_existing_customer_gets_draft_order(store):
    po = FakePowerOffice(customers=[{"id": "cust-1"}])
    out = run(store, FakeHubSpot(), po)
    assert out.outcome == "ordered"
    assert [p[0] for p in po.posts] == ["order"]  # no new customer (AC-03)
    payload = po.posts[0][1]
    assert payload["customerId"] == "cust-1"
    assert payload["reference"] == "hubspot-deal-42"
    assert payload["currencyCode"] == "NOK"
    assert len(payload["lines"]) == 1
    # AC-20: nothing here sends or books an invoice; only the draft create is called.
    assert "order-1" in out.reason
    row = last_outcome(store, 1)
    assert (row["outcome"], row["dry_run"]) == ("ordered", 0)
    assert COMPANY_NAME not in row["reason"]


def test_ac02_new_customer_created_then_order(store):
    po = FakePowerOffice()
    out = run(store, FakeHubSpot(), po)
    assert out.outcome == "ordered"
    assert po.posts[0] == ("customer", COMPANY_NAME, "123456785", "a@example.invalid", "NO")
    assert po.posts[1][1]["customerId"] == "cust-new"


def test_ac09_several_customers_held(store):
    po = FakePowerOffice(customers=[{"id": "a"}, {"id": "b"}])
    out = run(store, FakeHubSpot(), po)
    assert (out.outcome, out.reason) == ("held", "orgnr matches several customers")
    assert po.posts == []


@pytest.mark.parametrize("dry_run", [False, True])
def test_order_total_mismatch_held_before_any_customer_lookup_or_write(store, dry_run):
    po = FakePowerOffice()
    out = run(store, FakeHubSpot(amount="200"), po, dry_run=dry_run)
    assert (out.outcome, out.reason) == ("held", "order total does not match deal amount")
    assert po.customer_lookups == 0
    assert po.posts == []


def test_ac11_deal_not_found_held(store):
    out = run(store, FakeHubSpot(missing=True), FakePowerOffice())
    assert (out.outcome, out.reason) == ("held", "deal not found")
    assert last_outcome(store, 1)["outcome"] == "held"


def test_crm_read_failure_is_failed_not_held(store):
    out = run(store, FakeHubSpot(read_error=True), FakePowerOffice())
    assert (out.outcome, out.reason) == ("failed", "HubSpotError")


def test_not_won_deal_skipped(store):
    out = run(store, FakeHubSpot(stage="open"), FakePowerOffice())
    assert out.outcome == "skipped"


def test_ac13_accounting_failure_recorded_as_failed(store):
    po = FakePowerOffice(customers=[{"id": "cust-1"}], fail_order=True)
    out = run(store, FakeHubSpot(), po)
    assert (out.outcome, out.reason) == ("failed", "AccountingError")
    assert last_outcome(store, 1)["outcome"] == "failed"


def test_accounting_http_error_puts_status_code_and_fields_in_reason(store):
    class RejectingPowerOffice(FakePowerOffice):
        def create_order(self, payload):
            raise AccountingError(
                "POST /v2/SalesOrders returned 400",
                status=400,
                error_code="ValidationError",
                fields=["Lines[0].UnitPriceExVat"],
            )

    out = run(store, FakeHubSpot(), RejectingPowerOffice(customers=[{"id": "cust-1"}]))
    reason = "failed: AccountingError 400 ValidationError fields=Lines[0].UnitPriceExVat"
    assert (out.outcome, out.reason) == ("failed", reason)
    assert last_outcome(store, 1)["reason"] == reason


def test_event_processed_line_carries_ids_and_outcome(store, caplog):
    with caplog.at_level("INFO"):
        run(store, FakeHubSpot(stage="open"), FakePowerOffice())
    assert "event_id=1 deal_id=42 outcome=skipped" in caplog.text


def test_ac13_retry_finds_existing_order_and_creates_nothing(store):
    po = FakePowerOffice(orders=[{"id": "order-1", "reference": "hubspot-deal-42"}])
    out = run(store, FakeHubSpot(), po)
    assert (out.outcome, out.reason) == ("skipped", "order already exists")
    assert po.posts == []


def test_amount_event_after_order_not_handled(store):
    po = FakePowerOffice(orders=[{"id": "order-1"}])
    out = run(store, FakeHubSpot(), po, property_name="amount")
    assert (out.outcome, out.reason) == ("skipped", "change after order, not handled")


def test_ac18_dry_run_writes_nothing(store):
    po = FakePowerOffice()
    out = run(store, FakeHubSpot(), po, dry_run=True)
    assert po.posts == []
    assert out.outcome == "ordered" and out.dry_run
    assert "would create customer" in out.reason
    assert "would create order hubspot-deal-42" in out.reason
    assert COMPANY_NAME not in out.reason
    row = last_outcome(store, 1)
    assert (row["outcome"], row["dry_run"]) == ("ordered", 1)


# --- process_delivery (T11) ---


class PerDealHubSpot(FakeHubSpot):
    """Stage per deal id; a deal listed in `broken` fails its CRM read."""

    def __init__(self, stages, broken=()):
        super().__init__()
        self.stages = stages
        self.broken = set(broken)

    def get_deal(self, deal_id):
        if deal_id in self.broken:
            raise HubSpotError("CRM unreachable")
        self.stage = self.stages[deal_id]
        return super().get_deal(deal_id)


class OrderBookPowerOffice(FakePowerOffice):
    """Remembers created orders by reference, like the real system."""

    def __init__(self, customers=(), preexisting=()):
        super().__init__(customers=customers)
        self.book = {ref: {"id": "old"} for ref in preexisting}

    def find_orders(self, reference):
        return [self.book[reference]] if reference in self.book else []

    def create_order(self, payload):
        self.book[payload["reference"]] = {"id": "order-x"}
        return super().create_order(payload)


def ev(event_id, deal_id, property_name="dealstage"):
    return {
        "event_id": event_id,
        "deal_id": deal_id,
        "subscription_type": "deal.propertyChange",
        "property_name": property_name,
    }


def deliver(store, events, hubspot, po, dry_run=False):
    save_events(store, events)
    process = partial(
        process_delivery, hubspot=hubspot, poweroffice=po, store_path=store, dry_run=dry_run
    )
    return process("d1", events)  # same shape as the web callback process(delivery_id, events)


def mixed_events():
    return [ev(1, 10), ev(2, 11), ev(3, 12, "amount"), ev(4, 13)]


def mixed_hubspot():
    return PerDealHubSpot({"10": "open", "11": "open", "12": "won", "13": "won"}, broken={"13"})


def test_ac16_mixed_delivery_each_event_gets_own_outcome(store):
    po = OrderBookPowerOffice(customers=[{"id": "c"}], preexisting=["hubspot-deal-12"])
    counts = deliver(store, mixed_events(), mixed_hubspot(), po)
    assert counts == {"skipped": 3, "failed": 1}
    assert last_outcome(store, 3)["reason"] == "change after order, not handled"
    assert last_outcome(store, 4)["outcome"] == "failed"
    assert last_outcome(store, 4)["reason"] == "HubSpotError"
    assert last_outcome(store, 1)["outcome"] == "skipped"


def test_repeat_delivery_counts_final_events_as_duplicates(store):
    events = [ev(1, 10), ev(2, 11)]
    hs = PerDealHubSpot({"10": "open", "11": "open"})
    deliver(store, events, hs, OrderBookPowerOffice())
    counts = deliver(store, events, hs, OrderBookPowerOffice())
    assert counts == {"duplicate": 2}


def test_failed_event_is_retried_on_replay(store):
    events = [ev(1, 13)]
    deliver(store, events, PerDealHubSpot({"13": "open"}, broken={"13"}), OrderBookPowerOffice())
    assert last_outcome(store, 1)["outcome"] == "failed"
    counts = deliver(store, events, PerDealHubSpot({"13": "open"}), OrderBookPowerOffice())
    assert counts == {"skipped": 1}
    assert last_outcome(store, 1)["outcome"] == "skipped"


def test_held_event_keeps_its_outcome_on_replay(store):
    events = [ev(1, 10)]
    po = OrderBookPowerOffice(customers=[{"id": "a"}, {"id": "b"}])
    hs = PerDealHubSpot({"10": "won"})
    assert deliver(store, events, hs, po) == {"held": 1}
    assert deliver(store, events, hs, po) == {"duplicate": 1}
    assert last_outcome(store, 1)["outcome"] == "held"


def test_unexpected_exception_is_recorded_failed_and_run_continues(store):
    class Boom(PerDealHubSpot):
        def get_deal(self, deal_id):
            if deal_id == "10":
                raise ValueError("bug")
            return super().get_deal(deal_id)

    counts = deliver(store, [ev(1, 10), ev(2, 11)], Boom({"11": "open"}), OrderBookPowerOffice())
    assert counts == {"failed": 1, "skipped": 1}
    assert last_outcome(store, 1)["reason"] == "failed: ValueError"


def test_two_concurrent_deliveries_of_one_deal_create_one_order(store):
    events = [[ev(1, 10)], [ev(2, 10)]]
    save_events(store, events[0] + events[1])
    po = OrderBookPowerOffice(customers=[{"id": "c"}])
    hs = PerDealHubSpot({"10": "won"})
    process = partial(
        process_delivery, hubspot=hs, poweroffice=po, store_path=store, dry_run=False
    )
    threads = [
        threading.Thread(target=process, args=(f"d{i}", evs)) for i, evs in enumerate(events)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [p[0] for p in po.posts] == ["order"]
