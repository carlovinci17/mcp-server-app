import json

import azure.functions as func

from api import chat_handler


class FakeResponse:
    def __init__(self, output_text: str, response_id: str):
        self.output_text = output_text
        self.id = response_id


class FakeResponses:
    def __init__(self, response: FakeResponse):
        self._response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class FakeAgentClient:
    def __init__(self, response: FakeResponse):
        self.responses = FakeResponses(response)


def _request(body: dict) -> func.HttpRequest:
    return func.HttpRequest(method="POST", url="/api/chat", body=json.dumps(body).encode("utf-8"))


def test_chat_returns_reply_and_response_id(monkeypatch):
    fake_client = FakeAgentClient(FakeResponse("The office is in Melbourne.", "resp-001"))
    monkeypatch.setattr(chat_handler, "_get_agent_client", lambda: fake_client)

    response = chat_handler.chat(_request({"message": "Where is the office?"}))

    assert response.status_code == 200
    payload = json.loads(response.get_body())
    assert payload["reply"] == "The office is in Melbourne."
    assert payload["response_id"] == "resp-001"
    assert fake_client.responses.calls[0]["input"] == "Where is the office?"
    assert fake_client.responses.calls[0]["previous_response_id"] is None


def test_chat_threads_previous_response_id(monkeypatch):
    fake_client = FakeAgentClient(FakeResponse("follow-up", "resp-003"))
    monkeypatch.setattr(chat_handler, "_get_agent_client", lambda: fake_client)

    chat_handler.chat(
        _request({"message": "and part-time staff?", "previous_response_id": "resp-002"})
    )

    assert fake_client.responses.calls[0]["previous_response_id"] == "resp-002"


def test_chat_requires_message_field(monkeypatch):
    monkeypatch.setattr(
        chat_handler, "_get_agent_client", lambda: FakeAgentClient(FakeResponse("x", "y"))
    )

    response = chat_handler.chat(_request({}))

    assert response.status_code == 400
    assert "error" in json.loads(response.get_body())


def test_chat_rejects_invalid_json():
    request = func.HttpRequest(method="POST", url="/api/chat", body=b"not json")

    response = chat_handler.chat(request)

    assert response.status_code == 400


def test_chat_returns_503_when_foundry_not_configured(monkeypatch):
    def _raise():
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT / FOUNDRY_AGENT_NAME are not configured")

    monkeypatch.setattr(chat_handler, "_get_agent_client", _raise)

    response = chat_handler.chat(_request({"message": "hello"}))

    assert response.status_code == 503
