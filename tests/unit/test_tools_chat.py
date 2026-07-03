import json

import azure.functions as func

from src.models.chat import ChatJobStatus
from src.tools import chat


class FakeChatService:
    def __init__(
        self, start_result: ChatJobStatus | None = None, status_result: ChatJobStatus | None = None
    ):
        self._start_result = start_result
        self._status_result = status_result

    def start_message(self, message: str, previous_response_id: str | None = None):
        return self._start_result

    def get_message_status(self, response_id: str):
        return self._status_result


def _post_request(body: dict) -> func.HttpRequest:
    return func.HttpRequest(
        method="POST",
        url="/api/chat",
        body=json.dumps(body).encode("utf-8"),
    )


def _status_request(response_id: str | None) -> func.HttpRequest:
    params = {"id": response_id} if response_id else {}
    return func.HttpRequest(method="GET", url="/api/chat/status", body=b"", params=params)


def test_chat_starts_job_and_returns_status_json(monkeypatch):
    job = ChatJobStatus(response_id="resp-001", status="queued")
    monkeypatch.setattr(chat, "get_chat_service", lambda: FakeChatService(start_result=job))

    response = chat._start_chat(_post_request({"message": "Where is the office?"}))

    assert response.status_code == 200
    payload = json.loads(response.get_body())
    assert payload["response_id"] == "resp-001"
    assert payload["status"] == "queued"


def test_chat_requires_message_field(monkeypatch):
    job = ChatJobStatus(response_id="x", status="queued")
    monkeypatch.setattr(chat, "get_chat_service", lambda: FakeChatService(start_result=job))

    response = chat._start_chat(_post_request({}))

    assert response.status_code == 400
    payload = json.loads(response.get_body())
    assert "error" in payload


def test_chat_rejects_invalid_json():
    request = func.HttpRequest(method="POST", url="/api/chat", body=b"not json")

    response = chat._start_chat(request)

    assert response.status_code == 400


def test_chat_returns_503_when_foundry_not_configured(monkeypatch):
    def _raise():
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT / FOUNDRY_AGENT_NAME are not configured")

    monkeypatch.setattr(chat, "get_chat_service", _raise)

    response = chat._start_chat(_post_request({"message": "hello"}))

    assert response.status_code == 503


def test_chat_status_returns_completed_reply(monkeypatch):
    job = ChatJobStatus(
        response_id="resp-002", status="completed", reply="The remote work policy allows..."
    )
    monkeypatch.setattr(chat, "get_chat_service", lambda: FakeChatService(status_result=job))

    response = chat._chat_status(_status_request("resp-002"))

    assert response.status_code == 200
    payload = json.loads(response.get_body())
    assert payload["status"] == "completed"
    assert payload["reply"] == "The remote work policy allows..."


def test_chat_status_returns_in_progress(monkeypatch):
    job = ChatJobStatus(response_id="resp-003", status="in_progress")
    monkeypatch.setattr(chat, "get_chat_service", lambda: FakeChatService(status_result=job))

    response = chat._chat_status(_status_request("resp-003"))

    assert response.status_code == 200
    payload = json.loads(response.get_body())
    assert payload["status"] == "in_progress"
    assert payload["reply"] is None


def test_chat_status_requires_id_param():
    response = chat._chat_status(_status_request(None))

    assert response.status_code == 400


def test_chat_status_returns_503_when_foundry_not_configured(monkeypatch):
    def _raise():
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT / FOUNDRY_AGENT_NAME are not configured")

    monkeypatch.setattr(chat, "get_chat_service", _raise)

    response = chat._chat_status(_status_request("resp-004"))

    assert response.status_code == 503
