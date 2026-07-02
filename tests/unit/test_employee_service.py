import pytest

from src.services.employee_service import EmployeeNotFoundError, EmployeeService


def test_find_employee_matches_by_name(seeded_session_factory):
    service = EmployeeService(session_factory=seeded_session_factory)

    results = service.find_employee("Ada")

    assert [e.id for e in results] == ["emp-001"]


def test_find_employee_matches_by_department(seeded_session_factory):
    service = EmployeeService(session_factory=seeded_session_factory)

    results = service.find_employee("Engineering")

    assert {e.id for e in results} == {"emp-001", "emp-002"}


def test_get_employee_raises_for_unknown_id(seeded_session_factory):
    service = EmployeeService(session_factory=seeded_session_factory)

    with pytest.raises(EmployeeNotFoundError):
        service.get_employee("does-not-exist")


def test_list_departments_counts_employees(seeded_session_factory):
    service = EmployeeService(session_factory=seeded_session_factory)

    departments = service.list_departments()

    assert {d.name: d.employee_count for d in departments} == {"Engineering": 2}


def test_get_department_contacts_returns_only_that_department(seeded_session_factory):
    service = EmployeeService(session_factory=seeded_session_factory)

    contacts = service.get_department_contacts("Engineering")

    assert {c.id for c in contacts} == {"emp-001", "emp-002"}
