"""Load generated employees/customers/documents metadata from data/seed/ into
Azure SQL Database.

Requires AZURE_SQL_SERVER / AZURE_SQL_DATABASE to be set and the caller to be
authenticated via DefaultAzureCredential with db_datareader/db_datawriter (or
higher) on the target database. Run scripts/create_sample_data.py first.

Employees are loaded before customers/documents since both have FK references
to employees.id.
"""

import json
from datetime import date, datetime
from pathlib import Path

from src.core.logging import get_logger
from src.database.models import Base, CustomerRecord, DocumentMetadataRecord, EmployeeRecord
from src.database.sql import get_engine, get_session

logger = get_logger(__name__)

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"


def _load(name: str) -> list[dict]:
    return json.loads((SEED_DIR / name).read_text())


def main() -> None:
    Base.metadata.create_all(get_engine())

    employees = _load("employees.json")
    customers = _load("customers.json")
    documents = _load("documents.json")

    with get_session() as session:
        for e in employees:
            session.merge(EmployeeRecord(**e))
    logger.info("Loaded %d employees", len(employees))

    with get_session() as session:
        for c in customers:
            record = dict(c)
            if record.get("renewal_date"):
                record["renewal_date"] = date.fromisoformat(record["renewal_date"])
            session.merge(CustomerRecord(**record))
    logger.info("Loaded %d customers", len(customers))

    with get_session() as session:
        for d in documents:
            record = dict(d)
            record["created_at"] = datetime.fromisoformat(record["created_at"])
            record["updated_at"] = datetime.fromisoformat(record["updated_at"])
            session.merge(DocumentMetadataRecord(**record))
    logger.info("Loaded %d documents", len(documents))

    print(
        f"Loaded {len(employees)} employees, {len(customers)} customers, {len(documents)} documents"
    )


if __name__ == "__main__":
    main()
