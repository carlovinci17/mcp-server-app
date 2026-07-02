from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.database.models import EmployeeRecord
from src.database.sql import get_session
from src.models.employee import Department, Employee


class EmployeeNotFoundError(Exception):
    pass


def _to_employee(record: EmployeeRecord) -> Employee:
    return Employee(
        id=record.id,
        name=record.name,
        email=record.email,
        title=record.title,
        department=record.department,
        location=record.location,
        manager_id=record.manager_id,
    )


class EmployeeService:
    def __init__(
        self, session_factory: Callable[[], AbstractContextManager[Session]] = get_session
    ):
        self._session_factory = session_factory

    def find_employee(self, query: str, limit: int = 10) -> list[Employee]:
        like_pattern = f"%{query}%"
        with self._session_factory() as session:
            stmt = (
                select(EmployeeRecord)
                .where(
                    or_(
                        EmployeeRecord.name.ilike(like_pattern),
                        EmployeeRecord.email.ilike(like_pattern),
                        EmployeeRecord.department.ilike(like_pattern),
                        EmployeeRecord.title.ilike(like_pattern),
                    )
                )
                .limit(limit)
            )
            records = session.execute(stmt).scalars().all()
            return [_to_employee(r) for r in records]

    def get_employee(self, employee_id: str) -> Employee:
        with self._session_factory() as session:
            record = session.get(EmployeeRecord, employee_id)
            if record is None:
                raise EmployeeNotFoundError(employee_id)
            return _to_employee(record)

    def list_departments(self) -> list[Department]:
        with self._session_factory() as session:
            stmt = select(EmployeeRecord.department, func.count(EmployeeRecord.id)).group_by(
                EmployeeRecord.department
            )
            rows = session.execute(stmt).all()
            return [Department(name=name, employee_count=count) for name, count in rows]

    def get_department_contacts(self, department: str) -> list[Employee]:
        with self._session_factory() as session:
            stmt = select(EmployeeRecord).where(EmployeeRecord.department == department)
            records = session.execute(stmt).scalars().all()
            return [_to_employee(r) for r in records]
