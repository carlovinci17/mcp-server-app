import json

import azure.functions as func

from src.core.dependencies import get_chat_service

bp = func.Blueprint()


def _chat(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON"}),
            status_code=400,
            mimetype="application/json",
        )

    message = body.get("message")
    if not message:
        return func.HttpResponse(
            json.dumps({"error": "'message' is required"}),
            status_code=400,
            mimetype="application/json",
        )

    previous_response_id = body.get("previous_response_id")

    try:
        reply = get_chat_service().send_message(message, previous_response_id=previous_response_id)
    except RuntimeError as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=503,
            mimetype="application/json",
        )

    return func.HttpResponse(reply.model_dump_json(), status_code=200, mimetype="application/json")


@bp.route(route="chat", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def chat(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for the Vera chat frontend. Not an MCP tool - called
    directly by the browser-based chat UI, proxying to the Foundry agent.
    Anonymous auth level: this is meant to be called by anonymous browser
    visitors to the chat UI, unlike the MCP webhook which requires a system
    key. Restrict abuse via CORS (allowed origins) at the Function App level
    instead."""
    return _chat(req)
