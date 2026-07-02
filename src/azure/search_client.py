from functools import lru_cache

from azure.search.documents import SearchClient

from src.azure.identity import get_credential
from src.core.settings import get_settings


@lru_cache
def get_search_client() -> SearchClient:
    settings = get_settings()
    if not settings.search_enabled:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT is not configured")
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=get_credential(),
    )
