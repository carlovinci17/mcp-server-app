import azure.functions as func

from src.core.dependencies import get_search_service
from src.models.document import DocumentType
from src.tools._common import parse_enum_or_error

bp = func.Blueprint()


def _keyword_search(query: str, doc_type: str | None = None) -> str:
    parsed_type, error = parse_enum_or_error(DocumentType, doc_type)
    if error:
        return error
    results = get_search_service().keyword_search(query, doc_type=parsed_type)
    return results.model_dump_json()


def _semantic_search(query: str, doc_type: str | None = None) -> str:
    parsed_type, error = parse_enum_or_error(DocumentType, doc_type)
    if error:
        return error
    results = get_search_service().semantic_search(query, doc_type=parsed_type)
    return results.model_dump_json()


def _global_search(query: str) -> str:
    results = get_search_service().global_search(query)
    return results.model_dump_json()


@bp.mcp_tool()
def keyword_search(query: str, doc_type: str | None = None) -> str:
    """Full-text keyword search across all indexed content. Best for exact
    terms, names, or IDs. doc_type optionally filters to one of: document,
    policy, meeting_note, project_doc."""
    return _keyword_search(query, doc_type)


@bp.mcp_tool()
def semantic_search(query: str, doc_type: str | None = None) -> str:
    """Vector similarity search across all indexed content. Best for
    conceptual or natural-language questions where the exact wording may not
    match the source text. doc_type optionally filters to one of: document,
    policy, meeting_note, project_doc."""
    return _semantic_search(query, doc_type)


@bp.mcp_tool()
def global_search(query: str) -> str:
    """Hybrid keyword + vector search across all indexed content, with no
    type filtering. Use this as the default search when you're not sure
    whether keyword_search or semantic_search is the better fit."""
    return _global_search(query)
