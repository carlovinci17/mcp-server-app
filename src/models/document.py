from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    DOCUMENT = "document"
    POLICY = "policy"
    MEETING_NOTE = "meeting_note"
    PROJECT_DOC = "project_doc"


class DocumentMetadata(BaseModel):
    id: str
    title: str
    doc_type: DocumentType
    blob_container: str
    blob_path: str
    content_type: str = "text/markdown"
    department: str | None = None
    owner_id: str | None = Field(default=None, description="Employee ID of the document owner")
    tags: list[str] = Field(default_factory=list)
    related_document_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class Document(DocumentMetadata):
    content: str
