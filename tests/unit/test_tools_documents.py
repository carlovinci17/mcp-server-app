import json
from datetime import UTC

from src.services.document_service import DocumentNotFoundError
from src.tools import documents


class FakeDocumentService:
    def get_document(self, document_id: str):
        if document_id != "document-001":
            raise DocumentNotFoundError(document_id)
        from datetime import datetime

        from src.models.document import Document, DocumentType

        return Document(
            id="document-001",
            title="Onboarding Guide",
            doc_type=DocumentType.DOCUMENT,
            blob_container="documents",
            blob_path="document-001.md",
            department="Engineering",
            owner_id="emp-001",
            tags=["engineering"],
            related_document_ids=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            content="Full document body",
        )


def test_get_document_returns_valid_json(monkeypatch):
    monkeypatch.setattr(documents, "get_document_service", lambda: FakeDocumentService())

    result = documents._get_document("document-001")

    payload = json.loads(result)
    assert payload["id"] == "document-001"
    assert payload["content"] == "Full document body"


def test_get_document_reports_not_found_as_json_error(monkeypatch):
    monkeypatch.setattr(documents, "get_document_service", lambda: FakeDocumentService())

    result = documents._get_document("missing-id")

    payload = json.loads(result)
    assert "error" in payload


def _unreachable_document_service():
    raise AssertionError("get_document_service() should not be called for an invalid doc_type")


def test_search_documents_reports_invalid_doc_type_as_json_error(monkeypatch):
    monkeypatch.setattr(documents, "get_document_service", _unreachable_document_service)

    result = documents._search_documents("onboarding", doc_type="not-a-real-type")

    payload = json.loads(result)
    assert "not-a-real-type" in payload["error"]


def test_list_documents_reports_invalid_doc_type_as_json_error(monkeypatch):
    monkeypatch.setattr(documents, "get_document_service", _unreachable_document_service)

    result = documents._list_documents(doc_type="not-a-real-type")

    payload = json.loads(result)
    assert "not-a-real-type" in payload["error"]
