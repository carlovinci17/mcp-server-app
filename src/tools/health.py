import json

import azure.functions as func
from sqlalchemy import text

from src.azure.blob_client import BlobClient
from src.core.settings import get_settings
from src.database.sql import get_session

bp = func.Blueprint()

_CAPABILITIES = {
    "documents": [
        "search_documents",
        "list_documents",
        "get_document",
        "get_document_metadata",
        "find_related_documents",
        "summarize_document",
    ],
    "policies": ["search_policies", "list_policies", "get_policy"],
    "meetings": ["search_meetings", "list_meetings", "summarize_meeting"],
    "employees": ["find_employee", "list_departments", "get_department_contacts"],
    "customers": ["search_customers", "get_customer", "list_customers"],
    "health": ["server_health", "list_capabilities"],
}


def _check_sql() -> str:
    settings = get_settings()
    if not settings.sql_enabled:
        return "not_configured"
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


def _check_blob() -> str:
    settings = get_settings()
    if not settings.blob_enabled:
        return "not_configured"
    try:
        BlobClient().list_blobs(container="documents")
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


def _server_health() -> str:
    settings = get_settings()
    return json.dumps(
        {
            "status": "ok",
            "environment": settings.environment,
            "dependencies": {
                "sql": _check_sql(),
                "blob_storage": _check_blob(),
                "search": "not_configured" if not settings.search_enabled else "configured",
                "key_vault": "not_configured" if not settings.key_vault_enabled else "configured",
                "app_configuration": (
                    "not_configured" if not settings.app_config_enabled else "configured"
                ),
                "application_insights": (
                    "not_configured" if not settings.telemetry_enabled else "configured"
                ),
            },
        }
    )


def _list_capabilities() -> str:
    return json.dumps(_CAPABILITIES)


@bp.mcp_tool()
def server_health() -> str:
    """Report server health and connectivity status for each configured Azure dependency."""
    return _server_health()


@bp.mcp_tool()
def list_capabilities() -> str:
    """List all MCP tool categories and the tools available in each."""
    return _list_capabilities()
