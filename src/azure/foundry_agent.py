from functools import lru_cache

from azure.ai.projects import AIProjectClient
from openai import OpenAI

from src.azure.identity import get_credential
from src.core.settings import get_settings


@lru_cache
def get_project_client() -> AIProjectClient:
    settings = get_settings()
    if not settings.foundry_agent_enabled:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT / FOUNDRY_AGENT_NAME are not configured")
    return AIProjectClient(endpoint=settings.foundry_project_endpoint, credential=get_credential())


@lru_cache
def get_agent_client() -> OpenAI:
    settings = get_settings()
    return get_project_client().get_openai_client(agent_name=settings.foundry_agent_name)
