import json

import azure.functions as func

from src.core.dependencies import get_customer_service
from src.models.customer import CustomerStatus
from src.services.customer_service import CustomerNotFoundError
from src.tools._common import parse_enum_or_error

bp = func.Blueprint()


def _search_customers(query: str) -> str:
    customers = get_customer_service().search_customers(query)
    return json.dumps([c.model_dump(mode="json") for c in customers])


def _get_customer(customer_id: str) -> str:
    try:
        customer = get_customer_service().get_customer(customer_id)
    except CustomerNotFoundError:
        return json.dumps({"error": f"Customer '{customer_id}' not found"})
    return customer.model_dump_json()


def _list_customers(status: str | None = None, limit: int = 20) -> str:
    parsed_status, error = parse_enum_or_error(CustomerStatus, status)
    if error:
        return error
    customers = get_customer_service().list_customers(status=parsed_status, limit=limit)
    return json.dumps([c.model_dump(mode="json") for c in customers])


@bp.mcp_tool()
def search_customers(query: str) -> str:
    """Search customers by name, industry, or region."""
    return _search_customers(query)


@bp.mcp_tool()
def get_customer(customer_id: str) -> str:
    """Retrieve a customer's details by ID."""
    return _get_customer(customer_id)


@bp.mcp_tool()
def list_customers(status: str | None = None, limit: int = 20) -> str:
    """List customers, optionally filtered by status: prospect, active, or
    churned. Returns at most `limit` results (default 20, capped at 100)."""
    return _list_customers(status, limit)
