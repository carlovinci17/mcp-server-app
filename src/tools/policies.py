import json

import azure.functions as func

from src.core.dependencies import get_document_service
from src.models.document import DocumentType
from src.services.document_service import DocumentNotFoundError
from src.tools._common import report_database_unavailable

bp = func.Blueprint()

_DOC_TYPE = DocumentType.POLICY


@report_database_unavailable
def _search_policies(query: str) -> str:
    results = get_document_service().search_documents(query, doc_type=_DOC_TYPE)
    return results.model_dump_json()


@report_database_unavailable
def _list_policies(department: str | None = None) -> str:
    policies = get_document_service().list_documents(doc_type=_DOC_TYPE, department=department)
    return json.dumps([p.model_dump(mode="json") for p in policies])


@report_database_unavailable
def _get_policy(policy_id: str) -> str:
    try:
        doc = get_document_service().get_document(policy_id)
    except DocumentNotFoundError:
        return json.dumps({"error": f"Policy '{policy_id}' not found"})
    return doc.model_dump_json()


@bp.mcp_tool()
def search_policies(query: str) -> str:
    """Search company policies by title or department."""
    return _search_policies(query)


@bp.mcp_tool()
def list_policies(department: str | None = None) -> str:
    """List company policies, optionally filtered by department."""
    return _list_policies(department)


@bp.mcp_tool()
def get_policy(policy_id: str) -> str:
    """Retrieve a company policy's full content and metadata by ID."""
    return _get_policy(policy_id)
