from pydantic import BaseModel

from src.models.document import DocumentType


class SearchHit(BaseModel):
    id: str
    title: str
    doc_type: DocumentType
    snippet: str
    score: float


class SearchResults(BaseModel):
    query: str
    hits: list[SearchHit]
