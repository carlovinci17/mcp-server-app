import json

import azure.functions as func

from src.core.dependencies import get_document_service
from src.models.document import DocumentType
from src.services.document_service import DocumentNotFoundError

bp = func.Blueprint()

_DOC_TYPE = DocumentType.MEETING_NOTE


def _search_meetings(query: str) -> str:
    results = get_document_service().search_documents(query, doc_type=_DOC_TYPE)
    return results.model_dump_json()


def _list_meetings(department: str | None = None) -> str:
    meetings = get_document_service().list_documents(doc_type=_DOC_TYPE, department=department)
    return json.dumps([m.model_dump(mode="json") for m in meetings])


def _summarize_meeting(meeting_id: str) -> str:
    try:
        doc = get_document_service().get_document(meeting_id)
    except DocumentNotFoundError:
        return json.dumps({"error": f"Meeting note '{meeting_id}' not found"})
    return doc.model_dump_json()


@bp.mcp_tool()
def search_meetings(query: str) -> str:
    """Search meeting notes by title or department."""
    return _search_meetings(query)


@bp.mcp_tool()
def list_meetings(department: str | None = None) -> str:
    """List meeting notes, optionally filtered by department. Returns at
    most 20 results; filter by department or use search_meetings for a
    targeted lookup instead of listing everything."""
    return _list_meetings(department)


@bp.mcp_tool()
def summarize_meeting(meeting_id: str) -> str:
    """Retrieve a meeting note's full content for summarization. This tool
    returns the source content rather than summarizing server-side; use the
    returned content to produce the summary."""
    return _summarize_meeting(meeting_id)
