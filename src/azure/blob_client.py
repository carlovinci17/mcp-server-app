from functools import lru_cache

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from src.azure.identity import get_credential
from src.core.settings import get_settings


class BlobNotFoundError(Exception):
    pass


@lru_cache
def get_blob_service_client() -> BlobServiceClient:
    settings = get_settings()
    if not settings.blob_enabled:
        raise RuntimeError("AZURE_STORAGE_ACCOUNT_URL is not configured")
    return BlobServiceClient(
        account_url=settings.azure_storage_account_url,
        credential=get_credential(),
    )


class BlobClient:
    def __init__(self, service_client: BlobServiceClient | None = None):
        self._client = service_client or get_blob_service_client()

    def download_text(self, container: str, blob_path: str) -> str:
        try:
            blob = self._client.get_blob_client(container=container, blob=blob_path)
            return blob.download_blob().readall().decode("utf-8")
        except ResourceNotFoundError as exc:
            raise BlobNotFoundError(f"{container}/{blob_path} not found") from exc

    def upload_text(
        self, container: str, blob_path: str, content: str, overwrite: bool = True
    ) -> None:
        blob = self._client.get_blob_client(container=container, blob=blob_path)
        blob.upload_blob(content.encode("utf-8"), overwrite=overwrite)

    def list_blobs(self, container: str, prefix: str | None = None) -> list[str]:
        container_client = self._client.get_container_client(container)
        return [b.name for b in container_client.list_blobs(name_starts_with=prefix)]
