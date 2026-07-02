from src.services.chat_service import ChatService


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


def test_send_message_returns_reply_and_response_id():
    fake_client = FakeAgentClient(FakeResponse("The remote work policy allows...", "resp-001"))
    service = ChatService(agent_client=fake_client)

    reply = service.send_message("What's the remote work policy?")

    assert reply.reply == "The remote work policy allows..."
    assert reply.response_id == "resp-001"


def test_send_message_omits_previous_response_id_when_none():
    # The API rejects an explicit `previous_response_id: null` on the first
    # message of a conversation - the key must be absent, not None.
    fake_client = FakeAgentClient(FakeResponse("answer", "resp-002"))
    service = ChatService(agent_client=fake_client)

    service.send_message("hello")

    assert fake_client.responses.calls[0]["input"] == "hello"
    assert "previous_response_id" not in fake_client.responses.calls[0]


def test_send_message_threads_previous_response_id():
    fake_client = FakeAgentClient(FakeResponse("follow-up answer", "resp-004"))
    service = ChatService(agent_client=fake_client)

    service.send_message("and what about part-time staff?", previous_response_id="resp-003")

    assert fake_client.responses.calls[0]["previous_response_id"] == "resp-003"
