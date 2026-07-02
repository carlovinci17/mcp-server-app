"""Create (or update) the Azure AI Search index used for vector search.

Requires AZURE_SEARCH_ENDPOINT to be set and the caller to be authenticated
via DefaultAzureCredential with Search Service Contributor on the target
search service. Safe to re-run: SearchIndexClient.create_or_update_index is
idempotent.

text-embedding-3-small produces 1536-dimensional vectors; this index's
content_vector field is sized to match.
"""

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from src.azure.identity import get_credential
from src.core.settings import get_settings

_EMBEDDING_DIMENSIONS = 1536
_VECTOR_PROFILE_NAME = "default-vector-profile"
_VECTOR_ALGORITHM_NAME = "hnsw-config"


def build_index(index_name: str) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=_EMBEDDING_DIMENSIONS,
            vector_search_profile_name=_VECTOR_PROFILE_NAME,
        ),
        SimpleField(
            name="doc_type", type=SearchFieldDataType.String, filterable=True, facetable=True
        ),
        SimpleField(
            name="department", type=SearchFieldDataType.String, filterable=True, facetable=True
        ),
        SimpleField(
            name="tags",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True,
        ),
        SimpleField(name="blob_container", type=SearchFieldDataType.String),
        SimpleField(name="blob_path", type=SearchFieldDataType.String),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=_VECTOR_ALGORITHM_NAME)],
        profiles=[
            VectorSearchProfile(
                name=_VECTOR_PROFILE_NAME,
                algorithm_configuration_name=_VECTOR_ALGORITHM_NAME,
            )
        ],
    )

    return SearchIndex(name=index_name, fields=fields, vector_search=vector_search)


def main() -> None:
    settings = get_settings()
    if not settings.search_enabled:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT is not configured")

    client = SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=get_credential())
    index = build_index(settings.azure_search_index_name)
    result = client.create_or_update_index(index)
    print(f"Index '{result.name}' created/updated with {len(result.fields)} fields")


if __name__ == "__main__":
    main()
