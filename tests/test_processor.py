import pytest

from app.clients.hubspot import Company, Deal, DealNotFound, HubSpotError, LineItem
from app.clients.poweroffice import AccountingError
from app.processor import process_event
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
    def __init__(self, stage="won", orgnr="123456785", missing=False, read_error=False):
        self.stage = stage
        self.orgnr = orgnr
        self.missing = missing
        self.read_error = read_error

    def get_deal(self, deal_id):
        if self.missing:
            raise DealNotFound("404")
        if self.read_error:
            raise HubSpotError("CRM unreachable")
        return Deal(
            id=deal_id,
            properties={"dealstage": self.stage, "pipeline": "p1", "deal_currency_code": "NOK"},
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

    def find_customers(self, orgnr):
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
