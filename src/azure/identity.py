from functools import lru_cache

from azure.identity import DefaultAzureCredential


@lru_cache
def get_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()
