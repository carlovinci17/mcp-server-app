import json
from datetime import date

from src.services.customer_service import CustomerNotFoundError
from src.tools import customers


class FakeCustomerService:
    def get_customer(self, customer_id: str):
        if customer_id != "cust-001":
            raise CustomerNotFoundError(customer_id)
        from src.models.customer import Customer, CustomerStatus

        return Customer(
            id="cust-001",
            name="North Summit Systems",
            industry="Financial Services",
            region="Victoria",
            status=CustomerStatus.ACTIVE,
            account_owner_id="emp-001",
            renewal_date=date(2026, 12, 1),
        )

    def list_customers(self, status=None, limit=20):
        return [self.get_customer("cust-001")]


def test_get_customer_reports_not_found_as_json_error(monkeypatch):
    monkeypatch.setattr(customers, "get_customer_service", lambda: FakeCustomerService())

    result = customers._get_customer("missing-id")

    payload = json.loads(result)
    assert "error" in payload


def test_list_customers_returns_valid_json(monkeypatch):
    monkeypatch.setattr(customers, "get_customer_service", lambda: FakeCustomerService())

    result = customers._list_customers(status="active")

    payload = json.loads(result)
    assert payload[0]["id"] == "cust-001"


def test_list_customers_reports_invalid_status_as_json_error(monkeypatch):
    def _unreachable():
        raise AssertionError("get_customer_service() should not be called for an invalid status")

    monkeypatch.setattr(customers, "get_customer_service", _unreachable)

    result = customers._list_customers(status="not-a-real-status")

    payload = json.loads(result)
    assert "not-a-real-status" in payload["error"]
