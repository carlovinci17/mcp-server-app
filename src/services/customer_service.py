from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.database.models import CustomerRecord
from src.database.sql import get_session
from src.models.customer import Customer, CustomerStatus


class CustomerNotFoundError(Exception):
    pass


_MAX_LIST_LIMIT = 100


def _to_customer(record: CustomerRecord) -> Customer:
    return Customer(
        id=record.id,
        name=record.name,
        industry=record.industry,
        region=record.region,
        status=CustomerStatus(record.status),
        account_owner_id=record.account_owner_id,
        renewal_date=record.renewal_date,
    )


class CustomerService:
    def __init__(
        self, session_factory: Callable[[], AbstractContextManager[Session]] = get_session
    ):
        self._session_factory = session_factory

    def search_customers(self, query: str, limit: int = 10) -> list[Customer]:
        like_pattern = f"%{query}%"
        with self._session_factory() as session:
            stmt = (
                select(CustomerRecord)
                .where(
                    or_(
                        CustomerRecord.name.ilike(like_pattern),
                        CustomerRecord.industry.ilike(like_pattern),
                        CustomerRecord.region.ilike(like_pattern),
                    )
                )
                .limit(limit)
            )
            records = session.execute(stmt).scalars().all()
            return [_to_customer(r) for r in records]

    def get_customer(self, customer_id: str) -> Customer:
        with self._session_factory() as session:
            record = session.get(CustomerRecord, customer_id)
            if record is None:
                raise CustomerNotFoundError(customer_id)
            return _to_customer(record)

    def list_customers(
        self, status: CustomerStatus | None = None, limit: int = 20
    ) -> list[Customer]:
        limit = max(1, min(limit, _MAX_LIST_LIMIT))
        with self._session_factory() as session:
            stmt = select(CustomerRecord)
            if status is not None:
                stmt = stmt.where(CustomerRecord.status == status.value)
            records = session.execute(stmt.limit(limit)).scalars().all()
            return [_to_customer(r) for r in records]
