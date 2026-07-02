"""Chat proxy logic for the Vera console frontend.

This is a small, self-contained Azure Functions app - deployed independently
by Static Web Apps' Managed Functions (Free tier), separate from the main MCP
server app. It deliberately doesn't share code with src/ (that app is a
different deployment unit with a different requirements.txt); it only calls
an existing, pre-configured Azure AI Foundry agent, which in turn calls the
main MCP server as its own tool backend.
"""

import json
import os
from functools import lru_cache

import azure.functions as func
from azure.ai.projects import AIProjectClient

from azure.identity import DefaultAzureCredential


@lru_cache
def _get_agent_client():
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    agent_name = os.environ.get("FOUNDRY_AGENT_NAME")
    if not endpoint or not agent_name:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT / FOUNDRY_AGENT_NAME are not configured")
    project_client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    return project_client.get_openai_client(agent_name=agent_name)


def _error(message: str, status_code: int) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": message}), status_code=status_code, mimetype="application/json"
    )


def chat(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _error("Request body must be valid JSON", 400)

    message = body.get("message")
    if not message:
        return _error("'message' is required", 400)

    previous_response_id = body.get("previous_response_id")

    try:
        agent_client = _get_agent_client()
    except RuntimeError as exc:
        return _error(str(exc), 503)

    response = agent_client.responses.create(
        input=message,
        previous_response_id=previous_response_id,
    )

    return func.HttpResponse(
        json.dumps({"reply": response.output_text, "response_id": response.id}),
        status_code=200,
        mimetype="application/json",
    )
