from enum import StrEnum

from pydantic import BaseModel


class CustomerStatus(StrEnum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    CHURNED = "churned"


class Customer(BaseModel):
    id: str
    name: str
    industry: str
    region: str
    status: CustomerStatus
    account_owner_id: str | None = None
