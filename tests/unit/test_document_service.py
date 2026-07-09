from datetime import UTC, datetime

import pytest

from src.database.models import DocumentMetadataRecord
from src.models.document import DocumentType
from src.services.document_service import DocumentNotFoundError, DocumentService


class FakeBlobClient:
    def __init__(self, content: str = "# Fake content"):
        self.content = content
        self.calls = []

    def download_text(self, container: str, blob_path: str) -> str:
        self.calls.append((container, blob_path))
        return self.content


def test_get_document_metadata_returns_expected_fields(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    metadata = service.get_document_metadata("document-001")

    assert metadata.title == "Onboarding Guide - Engineering"
    assert metadata.doc_type == DocumentType.DOCUMENT
    assert metadata.department == "Engineering"
    assert metadata.related_document_ids == ["document-002"]


def test_get_document_metadata_raises_for_unknown_id(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    with pytest.raises(DocumentNotFoundError):
        service.get_document_metadata("does-not-exist")


def test_get_document_merges_metadata_and_blob_content(seeded_session_factory):
    blob_client = FakeBlobClient(content="# Onboarding Guide\n\nWelcome to the team.")
    service = DocumentService(blob_client=blob_client, session_factory=seeded_session_factory)

    document = service.get_document("document-001")

    assert document.content == "# Onboarding Guide\n\nWelcome to the team."
    assert blob_client.calls == [("documents", "document-001.md")]


def test_list_documents_filters_by_doc_type(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    policies = service.list_documents(doc_type=DocumentType.POLICY)

    assert [p.id for p in policies] == ["policy-001"]


def test_list_documents_filters_by_department(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    docs = service.list_documents(department="Engineering")

    assert {d.id for d in docs} == {"document-001", "document-002"}


def test_search_documents_matches_title_case_insensitively(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    results = service.search_documents("onboarding")

    assert results.query == "onboarding"
    assert [hit.id for hit in results.hits] == ["document-001"]


def test_search_documents_returns_no_hits_for_unmatched_query(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    results = service.search_documents("nonexistent-topic-xyz")

    assert results.hits == []


def test_find_related_documents_resolves_ids(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    related = service.find_related_documents("document-001")

    assert [r.id for r in related] == ["document-002"]


def test_find_related_documents_skips_dangling_ids_instead_of_raising(seeded_session_factory):
    now = datetime.now(UTC)
    with seeded_session_factory() as session:
        session.add(
            DocumentMetadataRecord(
                id="document-003",
                title="Doc With A Stale Reference",
                doc_type="document",
                blob_container="documents",
                blob_path="document-003.md",
                content_type="text/markdown",
                department="Engineering",
                owner_id="emp-001",
                tags=[],
                related_document_ids=["document-002", "does-not-exist"],
                created_at=now,
                updated_at=now,
            )
        )
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    related = service.find_related_documents("document-003")

    assert [r.id for r in related] == ["document-002"]


def test_list_documents_caps_limit_at_max(seeded_session_factory):
    service = DocumentService(blob_client=FakeBlobClient(), session_factory=seeded_session_factory)

    docs = service.list_documents(limit=10_000)

    assert len(docs) == 3  # every seeded document, not an error - the cap just bounds the query
