from src.models.document import DocumentType
from src.services.search_service import SearchService


class FakeSearchClient:
    def __init__(self, search_results=None):
        self.search_results = search_results or []
        self.search_calls = []
        self.uploaded_documents = []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return self.search_results

    def merge_or_upload_documents(self, documents):
        self.uploaded_documents.extend(documents)


def fake_embed(text: str) -> list[float]:
    return [0.1, 0.2, 0.3]


def _result(doc_id: str, score: float = 1.5) -> dict:
    return {
        "id": doc_id,
        "title": f"Title for {doc_id}",
        "content": "Some fictional content that is longer than a snippet.",
        "doc_type": "document",
        "@search.score": score,
    }


def test_index_document_embeds_content_and_uploads():
    client = FakeSearchClient()
    service = SearchService(search_client=client, embed_fn=fake_embed)

    service.index_document(
        document_id="document-001",
        title="Onboarding Guide",
        content="Welcome to the team.",
        doc_type=DocumentType.DOCUMENT,
        department="Engineering",
        tags=["engineering"],
        blob_container="documents",
        blob_path="document-001.md",
    )

    assert len(client.uploaded_documents) == 1
    uploaded = client.uploaded_documents[0]
    assert uploaded["id"] == "document-001"
    assert uploaded["content_vector"] == [0.1, 0.2, 0.3]
    assert uploaded["doc_type"] == "document"


def test_keyword_search_applies_doc_type_filter():
    client = FakeSearchClient(search_results=[_result("document-001")])
    service = SearchService(search_client=client, embed_fn=fake_embed)

    results = service.keyword_search("onboarding", doc_type=DocumentType.DOCUMENT)

    assert results.hits[0].id == "document-001"
    assert results.hits[0].score == 1.5
    assert client.search_calls[0]["filter"] == "doc_type eq 'document'"
    assert client.search_calls[0]["search_text"] == "onboarding"


def test_keyword_search_without_doc_type_has_no_filter():
    client = FakeSearchClient(search_results=[])
    service = SearchService(search_client=client, embed_fn=fake_embed)

    service.keyword_search("onboarding")

    assert client.search_calls[0]["filter"] is None


def test_semantic_search_uses_vector_query_and_no_search_text():
    client = FakeSearchClient(search_results=[_result("document-002")])
    service = SearchService(search_client=client, embed_fn=fake_embed)

    results = service.semantic_search("team onboarding process")

    assert results.hits[0].id == "document-002"
    call = client.search_calls[0]
    assert call["search_text"] is None
    assert call["vector_queries"][0].vector == [0.1, 0.2, 0.3]


def test_global_search_combines_keyword_and_vector():
    client = FakeSearchClient(search_results=[_result("document-003")])
    service = SearchService(search_client=client, embed_fn=fake_embed)

    results = service.global_search("onboarding")

    assert results.hits[0].id == "document-003"
    call = client.search_calls[0]
    assert call["search_text"] == "onboarding"
    assert call["vector_queries"][0].vector == [0.1, 0.2, 0.3]
