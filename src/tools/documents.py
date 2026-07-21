import json

import azure.functions as func

from src.core.dependencies import get_document_service
from src.models.document import DocumentType
from src.services.document_service import DocumentNotFoundError
from src.tools._common import parse_enum_or_error, report_database_unavailable

bp = func.Blueprint()


def _not_found(document_id: str) -> str:
    return json.dumps({"error": f"Document '{document_id}' not found"})


@report_database_unavailable
def _search_documents(query: str, doc_type: str | None = None) -> str:
    parsed_type, error = parse_enum_or_error(DocumentType, doc_type)
    if error:
        return error
    results = get_document_service().search_documents(query, doc_type=parsed_type)
    return results.model_dump_json()


@report_database_unavailable
def _list_documents(
    doc_type: str | None = None, department: str | None = None, limit: int = 20
) -> str:
    parsed_type, error = parse_enum_or_error(DocumentType, doc_type)
    if error:
        return error
    docs = get_document_service().list_documents(
        doc_type=parsed_type, department=department, limit=limit
    )
    return json.dumps([d.model_dump(mode="json") for d in docs])


@report_database_unavailable
def _get_document(document_id: str) -> str:
    try:
        doc = get_document_service().get_document(document_id)
    except DocumentNotFoundError:
        return _not_found(document_id)
    return doc.model_dump_json()


@report_database_unavailable
def _get_document_metadata(document_id: str) -> str:
    try:
        metadata = get_document_service().get_document_metadata(document_id)
    except DocumentNotFoundError:
        return _not_found(document_id)
    return metadata.model_dump_json()


@report_database_unavailable
def _find_related_documents(document_id: str) -> str:
    try:
        related = get_document_service().find_related_documents(document_id)
    except DocumentNotFoundError:
        return _not_found(document_id)
    return json.dumps([d.model_dump(mode="json") for d in related])


@bp.mcp_tool()
def search_documents(query: str, doc_type: str | None = None) -> str:
    """Search documents, policies, meeting notes, and project docs by title,
    department, or tags. doc_type optionally filters to one of: document,
    policy, meeting_note, project_doc."""
    return _search_documents(query, doc_type)


@bp.mcp_tool()
def list_documents(
    doc_type: str | None = None, department: str | None = None, limit: int = 20
) -> str:
    """List documents, optionally filtered by document type or department.
    Returns at most `limit` results (default 20, capped at 100); increase it
    if you need more, but prefer search_documents for targeted lookups
    instead of listing everything."""
    return _list_documents(doc_type, department, limit)


@bp.mcp_tool()
def get_document(document_id: str) -> str:
    """Retrieve a document's full content and metadata by ID."""
    return _get_document(document_id)


@bp.mcp_tool()
def get_document_metadata(document_id: str) -> str:
    """Retrieve metadata (title, type, owner, department, tags) for a
    document without fetching its full content."""
    return _get_document_metadata(document_id)


@bp.mcp_tool()
def find_related_documents(document_id: str) -> str:
    """Find documents related to the given document ID."""
    return _find_related_documents(document_id)


@bp.mcp_tool()
def summarize_document(document_id: str) -> str:
    """Retrieve a document's full content for summarization. This tool
    returns the source content rather than summarizing server-side; use the
    returned content to produce the summary."""
    return _get_document(document_id)
