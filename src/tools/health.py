import json
import threading

import azure.functions as func
from sqlalchemy import text

from src.azure.blob_client import BlobClient
from src.core.logging import get_logger
from src.core.settings import get_settings
from src.database.sql import DatabaseUnavailableError, get_session

bp = func.Blueprint()
_logger = get_logger(__name__)

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
    "search": ["keyword_search", "semantic_search", "global_search"],
    "health": ["server_health", "list_capabilities"],
}

# Kept in sync by hand with each tool's docstring in src/tools/*.py - condensed
# to a single short sentence for display in the frontend's tools popup.
_TOOL_DESCRIPTIONS = {
    "search_customers": "Search customers by name, industry, or region.",
    "get_customer": "Retrieve a customer's details by ID.",
    "list_customers": "List customers, optionally filtered by status.",
    "search_documents": "Search documents, policies, meeting notes, and project docs.",
    "list_documents": "List documents, optionally filtered by type or department.",
    "get_document": "Retrieve a document's full content and metadata by ID.",
    "get_document_metadata": "Retrieve a document's metadata without its full content.",
    "find_related_documents": "Find documents related to a given document ID.",
    "summarize_document": "Retrieve a document's content for summarization.",
    "find_employee": "Find employees by name, email, department, or title.",
    "list_departments": "List all departments and their employee counts.",
    "get_department_contacts": "List all employees in a given department.",
    "server_health": "Report server health and Azure dependency connectivity.",
    "list_capabilities": "List all MCP tool categories and their tools.",
    "search_meetings": "Search meeting notes by title or department.",
    "list_meetings": "List meeting notes, optionally filtered by department.",
    "summarize_meeting": "Retrieve a meeting note's content for summarization.",
    "search_policies": "Search company policies by title or department.",
    "list_policies": "List company policies, optionally filtered by department.",
    "get_policy": "Retrieve a company policy's full content and metadata.",
    "keyword_search": "Full-text keyword search across all indexed content.",
    "semantic_search": "Vector similarity search for conceptual or natural-language queries.",
    "global_search": "Hybrid keyword + vector search across all indexed content.",
}


def _check_sql() -> str:
    settings = get_settings()
    if not settings.sql_enabled:
        return "not_configured"
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except DatabaseUnavailableError:
        return "paused: monthly free-tier limit reached"
    except Exception:
        # Full detail (hostnames, driver diagnostics) goes to the logs only -
        # server_health is an MCP tool response, not a trusted-operator surface.
        _logger.exception("SQL health check failed")
        return "error: unable to connect"


def _check_blob() -> str:
    settings = get_settings()
    if not settings.blob_enabled:
        return "not_configured"
    try:
        BlobClient().list_blobs(container="documents")
        return "ok"
    except Exception:
        _logger.exception("Blob health check failed")
        return "error: unable to connect"


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


def _health_http(req: func.HttpRequest) -> func.HttpResponse:
    # Kick off the SQL/Blob connection attempts (what actually wakes a
    # paused Azure SQL Serverless database) without waiting for them to
    # finish - the caller (browser startup ping) discards the response
    # either way, and blocking here risks exceeding SWA's ~45s hard timeout
    # on its linked backend while SQL resumes from auto-pause.
    threading.Thread(target=_check_sql, daemon=True).start()
    threading.Thread(target=_check_blob, daemon=True).start()
    body = json.dumps({"status": "warming"})
    return func.HttpResponse(body, status_code=200, mimetype="application/json")


@bp.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for the chat frontend's startup check. Not an MCP tool -
    called by the browser on page load to warm up SQL/Blob connectivity
    before the visitor sends their first message. Returns immediately
    without waiting for the checks to complete; the caller doesn't read the
    response. Anonymous auth level, same reasoning as the /api/chat
    endpoint."""
    return _health_http(req)


@bp.mcp_tool()
def list_capabilities() -> str:
    """List all MCP tool categories and the tools available in each."""
    return _list_capabilities()


def _list_tools() -> str:
    groups = [
        {
            "category": category,
            "tools": [
                {"name": name, "description": _TOOL_DESCRIPTIONS.get(name, "")}
                for name in tool_names
            ],
        }
        for category, tool_names in _CAPABILITIES.items()
    ]
    return json.dumps({"groups": groups})


def _tools_http(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(_list_tools(), status_code=200, mimetype="application/json")


@bp.route(route="tools", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def tools_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for the chat frontend's "MCP Server Tools" popup. Not an
    MCP tool itself - lists the real registered tools, grouped by category,
    with brief descriptions. Anonymous auth level, same reasoning as the
    other /api/* endpoints."""
    return _tools_http(req)
