import json

import azure.functions as func

from src.models.chat import ChatReply
from src.tools import chat


class FakeChatService:
    def __init__(self, reply: ChatReply):
        self._reply = reply

    def send_message(self, message: str, previous_response_id: str | None = None):
        return self._reply


def _request(body: dict) -> func.HttpRequest:
    return func.HttpRequest(
        method="POST",
        url="/api/chat",
        body=json.dumps(body).encode("utf-8"),
    )


def test_chat_returns_reply_json(monkeypatch):
    fake_reply = ChatReply(reply="The office is in Melbourne.", response_id="resp-001")
    monkeypatch.setattr(chat, "get_chat_service", lambda: FakeChatService(fake_reply))

    response = chat._chat(_request({"message": "Where is the office?"}))

    assert response.status_code == 200
    payload = json.loads(response.get_body())
    assert payload["reply"] == "The office is in Melbourne."
    assert payload["response_id"] == "resp-001"


def test_chat_requires_message_field(monkeypatch):
    monkeypatch.setattr(
        chat, "get_chat_service", lambda: FakeChatService(ChatReply(reply="x", response_id="y"))
    )

    response = chat._chat(_request({}))

    assert response.status_code == 400
    payload = json.loads(response.get_body())
    assert "error" in payload


def test_chat_rejects_invalid_json():
    request = func.HttpRequest(method="POST", url="/api/chat", body=b"not json")

    response = chat._chat(request)

    assert response.status_code == 400


def test_chat_returns_503_when_foundry_not_configured(monkeypatch):
    def _raise():
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT / FOUNDRY_AGENT_NAME are not configured")

    monkeypatch.setattr(chat, "get_chat_service", _raise)

    response = chat._chat(_request({"message": "hello"}))

    assert response.status_code == 503
