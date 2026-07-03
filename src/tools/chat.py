import json

import azure.functions as func

from src.core.dependencies import get_chat_service

bp = func.Blueprint()


def _start_chat(req: func.HttpRequest) -> func.HttpResponse:
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
        job = get_chat_service().start_message(message, previous_response_id=previous_response_id)
    except RuntimeError as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=503,
            mimetype="application/json",
        )

    return func.HttpResponse(job.model_dump_json(), status_code=200, mimetype="application/json")


def _chat_status(req: func.HttpRequest) -> func.HttpResponse:
    response_id = req.params.get("id")
    if not response_id:
        return func.HttpResponse(
            json.dumps({"error": "'id' query parameter is required"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        job = get_chat_service().get_message_status(response_id)
    except RuntimeError as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=503,
            mimetype="application/json",
        )

    return func.HttpResponse(job.model_dump_json(), status_code=200, mimetype="application/json")


@bp.route(route="chat", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def chat(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for the Vera chat frontend. Not an MCP tool - called
    directly by the browser-based chat UI, proxying to the Foundry agent.
    Starts the agent run in background mode and returns immediately (status
    queued/in_progress) rather than blocking - a synchronous call can run well
    past Azure Static Web Apps' hard 45-second backend timeout for questions
    that chain several tool calls. The frontend polls /api/chat/status for
    completion. Anonymous auth level: this is meant to be called by anonymous
    browser visitors to the chat UI, unlike the MCP webhook which requires a
    system key. Restrict abuse via CORS (allowed origins) at the Function App
    level instead."""
    return _start_chat(req)


@bp.route(route="chat/status", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def chat_status(req: func.HttpRequest) -> func.HttpResponse:
    """Poll for the status/result of a background chat run started via
    POST /api/chat. Returns {response_id, status, reply?, error?}. status is
    "queued" or "in_progress" while still running, "completed" with reply
    set once done, or "failed"/"cancelled"/"incomplete" with error set."""
    return _chat_status(req)
