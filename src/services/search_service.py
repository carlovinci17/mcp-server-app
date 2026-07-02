import time
from collections.abc import Callable

from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from src.azure.embeddings import embed_text
from src.models.document import DocumentType
from src.models.search import SearchHit, SearchResults

_SNIPPET_LENGTH = 200

# Free-tier Azure AI Search throttles rapid write requests; batching uploads
# and backing off on 429s keeps bulk indexing reliable without upgrading tier.
_UPLOAD_BATCH_SIZE = 10
_UPLOAD_BATCH_DELAY_SECONDS = 1
_MAX_RETRIES = 5
_RETRY_BACKOFF_SECONDS = 5


def _to_hit(result: dict) -> SearchHit:
    content = result.get("content", "") or ""
    return SearchHit(
        id=result["id"],
        title=result["title"],
        doc_type=DocumentType(result["doc_type"]),
        snippet=content[:_SNIPPET_LENGTH],
        score=result.get("@search.score", 0.0),
    )


class SearchService:
    def __init__(
        self,
        search_client: SearchClient,
        embed_fn: Callable[[str], list[float]] = embed_text,
    ):
        self._client = search_client
        self._embed_fn = embed_fn

    def _build_payload(
        self,
        document_id: str,
        title: str,
        content: str,
        doc_type: DocumentType,
        department: str | None,
        tags: list[str],
        blob_container: str,
        blob_path: str,
    ) -> dict:
        return {
            "id": document_id,
            "title": title,
            "content": content,
            "content_vector": self._embed_fn(content),
            "doc_type": doc_type.value,
            "department": department,
            "tags": tags,
            "blob_container": blob_container,
            "blob_path": blob_path,
        }

    def index_document(
        self,
        document_id: str,
        title: str,
        content: str,
        doc_type: DocumentType,
        department: str | None,
        tags: list[str],
        blob_container: str,
        blob_path: str,
    ) -> None:
        payload = self._build_payload(
            document_id, title, content, doc_type, department, tags, blob_container, blob_path
        )
        self._client.merge_or_upload_documents(documents=[payload])

    def index_documents(self, items: list[dict]) -> None:
        """Bulk-embed and upload documents in small batches with retry/backoff,
        to stay under Free-tier Azure AI Search write-throttling limits.

        Each item must have the same keys as index_document's parameters:
        document_id, title, content, doc_type, department, tags,
        blob_container, blob_path.
        """
        payloads = [self._build_payload(**item) for item in items]

        for start in range(0, len(payloads), _UPLOAD_BATCH_SIZE):
            batch = payloads[start : start + _UPLOAD_BATCH_SIZE]
            self._upload_batch_with_retry(batch)
            time.sleep(_UPLOAD_BATCH_DELAY_SECONDS)

    def _upload_batch_with_retry(self, batch: list[dict]) -> None:
        for attempt in range(_MAX_RETRIES):
            try:
                self._client.merge_or_upload_documents(documents=batch)
                return
            except HttpResponseError as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
                del exc

    def keyword_search(
        self, query: str, doc_type: DocumentType | None = None, top: int = 10
    ) -> SearchResults:
        filter_expr = f"doc_type eq '{doc_type.value}'" if doc_type else None
        results = self._client.search(search_text=query, filter=filter_expr, top=top)
        return SearchResults(query=query, hits=[_to_hit(r) for r in results])

    def semantic_search(
        self, query: str, doc_type: DocumentType | None = None, top: int = 10
    ) -> SearchResults:
        vector = self._embed_fn(query)
        vector_query = VectorizedQuery(
            vector=vector, k_nearest_neighbors=top, fields="content_vector"
        )
        filter_expr = f"doc_type eq '{doc_type.value}'" if doc_type else None
        results = self._client.search(
            search_text=None, vector_queries=[vector_query], filter=filter_expr, top=top
        )
        return SearchResults(query=query, hits=[_to_hit(r) for r in results])

    def global_search(self, query: str, top: int = 10) -> SearchResults:
        vector = self._embed_fn(query)
        vector_query = VectorizedQuery(
            vector=vector, k_nearest_neighbors=top, fields="content_vector"
        )
        results = self._client.search(search_text=query, vector_queries=[vector_query], top=top)
        return SearchResults(query=query, hits=[_to_hit(r) for r in results])
