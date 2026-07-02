from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def _load_yaml_defaults() -> dict:
    with open(_CONFIG_DIR / "settings.yaml") as f:
        return yaml.safe_load(f)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"

    azure_sql_server: str | None = None
    azure_sql_database: str | None = None

    azure_storage_account_url: str | None = None

    azure_search_endpoint: str | None = None
    azure_search_index_name: str = "enterprise-knowledge-index"

    azure_openai_endpoint: str | None = None
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    azure_key_vault_url: str | None = None
    azure_appconfig_endpoint: str | None = None
    applicationinsights_connection_string: str | None = None

    foundry_project_endpoint: str | None = None
    foundry_agent_name: str | None = None

    @property
    def sql_enabled(self) -> bool:
        return bool(self.azure_sql_server and self.azure_sql_database)

    @property
    def blob_enabled(self) -> bool:
        return bool(self.azure_storage_account_url)

    @property
    def search_enabled(self) -> bool:
        return bool(self.azure_search_endpoint)

    @property
    def embeddings_enabled(self) -> bool:
        return bool(self.azure_openai_endpoint)

    @property
    def key_vault_enabled(self) -> bool:
        return bool(self.azure_key_vault_url)

    @property
    def app_config_enabled(self) -> bool:
        return bool(self.azure_appconfig_endpoint)

    @property
    def telemetry_enabled(self) -> bool:
        return bool(self.applicationinsights_connection_string)

    @property
    def foundry_agent_enabled(self) -> bool:
        return bool(self.foundry_project_endpoint and self.foundry_agent_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_yaml_config() -> dict:
    return _load_yaml_defaults()
