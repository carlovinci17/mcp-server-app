from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, CustomerRecord, DocumentMetadataRecord, EmployeeRecord


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def factory():
        session = maker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return factory


@pytest.fixture
def seeded_session_factory(session_factory):
    now = datetime.now(UTC)
    with session_factory() as session:
        session.add(
            EmployeeRecord(
                id="emp-001",
                name="Ada Lovelace",
                email="ada@vortexdigital.example",
                title="Engineering Manager",
                department="Engineering",
                location="Melbourne, VIC",
                manager_id=None,
            )
        )
        session.add(
            EmployeeRecord(
                id="emp-002",
                name="Grace Hopper",
                email="grace@vortexdigital.example",
                title="Software Engineer",
                department="Engineering",
                location="Remote - AU",
                manager_id="emp-001",
            )
        )
        session.add(
            CustomerRecord(
                id="cust-001",
                name="North Summit Systems",
                industry="Financial Services",
                region="Victoria",
                status="active",
                account_owner_id="emp-001",
            )
        )
        session.add(
            DocumentMetadataRecord(
                id="document-001",
                title="Onboarding Guide - Engineering",
                doc_type="document",
                blob_container="documents",
                blob_path="document-001.md",
                content_type="text/markdown",
                department="Engineering",
                owner_id="emp-001",
                tags=["engineering", "document"],
                related_document_ids=["document-002"],
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            DocumentMetadataRecord(
                id="document-002",
                title="Architecture Overview - Engineering",
                doc_type="document",
                blob_container="documents",
                blob_path="document-002.md",
                content_type="text/markdown",
                department="Engineering",
                owner_id="emp-002",
                tags=["engineering", "document"],
                related_document_ids=[],
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            DocumentMetadataRecord(
                id="policy-001",
                title="Remote Work Policy",
                doc_type="policy",
                blob_container="policies",
                blob_path="policy-001.md",
                content_type="text/markdown",
                department="Human Resources",
                owner_id="emp-001",
                tags=["human-resources", "policy"],
                related_document_ids=[],
                created_at=now,
                updated_at=now,
            )
        )
    return session_factory
