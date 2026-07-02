from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.azure.blob_client import BlobClient
from src.database.models import DocumentMetadataRecord
from src.database.sql import get_session
from src.models.document import Document, DocumentMetadata, DocumentType
from src.models.search import SearchHit, SearchResults


class DocumentNotFoundError(Exception):
    pass


def _to_metadata(record: DocumentMetadataRecord) -> DocumentMetadata:
    return DocumentMetadata(
        id=record.id,
        title=record.title,
        doc_type=DocumentType(record.doc_type),
        blob_container=record.blob_container,
        blob_path=record.blob_path,
        content_type=record.content_type,
        department=record.department,
        owner_id=record.owner_id,
        tags=list(record.tags or []),
        related_document_ids=list(record.related_document_ids or []),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class DocumentService:
    def __init__(
        self,
        blob_client: BlobClient,
        session_factory: Callable[[], AbstractContextManager[Session]] = get_session,
    ):
        self._blob = blob_client
        self._session_factory = session_factory

    def list_documents(
        self,
        doc_type: DocumentType | None = None,
        department: str | None = None,
        limit: int = 20,
    ) -> list[DocumentMetadata]:
        with self._session_factory() as session:
            stmt = select(DocumentMetadataRecord)
            if doc_type is not None:
                stmt = stmt.where(DocumentMetadataRecord.doc_type == doc_type.value)
            if department is not None:
                stmt = stmt.where(DocumentMetadataRecord.department == department)
            records = session.execute(stmt.limit(limit)).scalars().all()
            return [_to_metadata(r) for r in records]

    def get_document_metadata(self, document_id: str) -> DocumentMetadata:
        with self._session_factory() as session:
            record = session.get(DocumentMetadataRecord, document_id)
            if record is None:
                raise DocumentNotFoundError(document_id)
            return _to_metadata(record)

    def get_document(self, document_id: str) -> Document:
        metadata = self.get_document_metadata(document_id)
        content = self._blob.download_text(metadata.blob_container, metadata.blob_path)
        return Document(**metadata.model_dump(), content=content)

    def search_documents(
        self, query: str, doc_type: DocumentType | None = None, limit: int = 10
    ) -> SearchResults:
        like_pattern = f"%{query}%"
        with self._session_factory() as session:
            stmt = select(DocumentMetadataRecord).where(
                or_(
                    DocumentMetadataRecord.title.ilike(like_pattern),
                    DocumentMetadataRecord.department.ilike(like_pattern),
                )
            )
            if doc_type is not None:
                stmt = stmt.where(DocumentMetadataRecord.doc_type == doc_type.value)
            records = session.execute(stmt.limit(limit)).scalars().all()

        hits = [
            SearchHit(
                id=r.id,
                title=r.title,
                doc_type=DocumentType(r.doc_type),
                snippet=r.title,
                score=1.0,
            )
            for r in records
        ]
        return SearchResults(query=query, hits=hits)

    def find_related_documents(self, document_id: str) -> list[DocumentMetadata]:
        metadata = self.get_document_metadata(document_id)
        return [self.get_document_metadata(rid) for rid in metadata.related_document_ids]
