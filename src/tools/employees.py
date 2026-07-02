import json

import azure.functions as func

from src.core.dependencies import get_employee_service

bp = func.Blueprint()


def _find_employee(query: str) -> str:
    employees = get_employee_service().find_employee(query)
    return json.dumps([e.model_dump(mode="json") for e in employees])


def _list_departments() -> str:
    departments = get_employee_service().list_departments()
    return json.dumps([d.model_dump(mode="json") for d in departments])


def _get_department_contacts(department: str) -> str:
    employees = get_employee_service().get_department_contacts(department)
    return json.dumps([e.model_dump(mode="json") for e in employees])


@bp.mcp_tool()
def find_employee(query: str) -> str:
    """Find employees by name, email, department, or title."""
    return _find_employee(query)


@bp.mcp_tool()
def list_departments() -> str:
    """List all departments and their employee counts."""
    return _list_departments()


@bp.mcp_tool()
def get_department_contacts(department: str) -> str:
    """List all employees in a given department."""
    return _get_department_contacts(department)
