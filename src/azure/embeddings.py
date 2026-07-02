from functools import lru_cache

from openai import AzureOpenAI

from azure.identity import get_bearer_token_provider
from src.azure.identity import get_credential
from src.core.settings import get_settings

_COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"
_API_VERSION = "2024-10-21"


@lru_cache
def get_openai_client() -> AzureOpenAI:
    settings = get_settings()
    if not settings.embeddings_enabled:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured")
    token_provider = get_bearer_token_provider(get_credential(), _COGNITIVE_SERVICES_SCOPE)
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version=_API_VERSION,
    )


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    client = get_openai_client()
    response = client.embeddings.create(
        input=texts,
        model=settings.azure_openai_embedding_deployment,
    )
    return [item.embedding for item in response.data]
