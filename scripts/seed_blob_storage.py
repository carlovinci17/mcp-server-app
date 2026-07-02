"""Upload generated document content from data/seed/blobs/ to Azure Blob Storage.

Requires AZURE_STORAGE_ACCOUNT_URL to be set and the caller to be authenticated
via DefaultAzureCredential (e.g. `az login`) with Storage Blob Data Contributor
on the target account. Run scripts/create_sample_data.py first.
"""

from pathlib import Path

from src.azure.blob_client import BlobClient
from src.core.logging import get_logger

logger = get_logger(__name__)

BLOB_DIR = Path(__file__).resolve().parent.parent / "data" / "seed" / "blobs"


def main() -> None:
    client = BlobClient()
    uploaded = 0
    for container_dir in sorted(BLOB_DIR.iterdir()):
        if not container_dir.is_dir():
            continue
        container = container_dir.name
        for blob_file in sorted(container_dir.glob("*.md")):
            content = blob_file.read_text()
            client.upload_text(container=container, blob_path=blob_file.name, content=content)
            uploaded += 1
            logger.info("Uploaded %s/%s", container, blob_file.name)

    container_count = sum(1 for d in BLOB_DIR.iterdir() if d.is_dir())
    print(f"Uploaded {uploaded} blobs across {container_count} containers")


if __name__ == "__main__":
    main()
