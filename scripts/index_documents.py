"""Embed and push generated document content from data/seed/ into the Azure
AI Search index.

Requires AZURE_SEARCH_ENDPOINT and AZURE_OPENAI_ENDPOINT to be set, and the
caller to be authenticated via DefaultAzureCredential with Search Index Data
Contributor on the search service and Cognitive Services OpenAI User on the
Azure OpenAI resource. Run scripts/create_sample_data.py and
scripts/create_search_index.py first.
"""

import json
from pathlib import Path

from src.azure.search_client import get_search_client
from src.core.logging import get_logger
from src.models.document import DocumentType
from src.services.search_service import SearchService

logger = get_logger(__name__)

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
BLOB_DIR = SEED_DIR / "blobs"


def main() -> None:
    documents = json.loads((SEED_DIR / "documents.json").read_text())
    service = SearchService(search_client=get_search_client())

    items = []
    for doc in documents:
        content_path = BLOB_DIR / doc["blob_container"] / doc["blob_path"]
        items.append(
            {
                "document_id": doc["id"],
                "title": doc["title"],
                "content": content_path.read_text(),
                "doc_type": DocumentType(doc["doc_type"]),
                "department": doc["department"],
                "tags": doc["tags"],
                "blob_container": doc["blob_container"],
                "blob_path": doc["blob_path"],
            }
        )

    logger.info("Embedding and uploading %d documents in batches", len(items))
    service.index_documents(items)
    print(f"Indexed {len(items)} documents")


if __name__ == "__main__":
    main()
