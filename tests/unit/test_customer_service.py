import pytest

from src.models.customer import CustomerStatus
from src.services.customer_service import CustomerNotFoundError, CustomerService


def test_search_customers_matches_by_name(seeded_session_factory):
    service = CustomerService(session_factory=seeded_session_factory)

    results = service.search_customers("North Summit")

    assert [c.id for c in results] == ["cust-001"]


def test_get_customer_raises_for_unknown_id(seeded_session_factory):
    service = CustomerService(session_factory=seeded_session_factory)

    with pytest.raises(CustomerNotFoundError):
        service.get_customer("does-not-exist")


def test_list_customers_filters_by_status(seeded_session_factory):
    service = CustomerService(session_factory=seeded_session_factory)

    active = service.list_customers(status=CustomerStatus.ACTIVE)
    churned = service.list_customers(status=CustomerStatus.CHURNED)

    assert [c.id for c in active] == ["cust-001"]
    assert churned == []
