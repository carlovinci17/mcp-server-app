from src.services.chat_service import ChatService


class FakeResponse:
    def __init__(self, response_id: str, status: str, output_text: str | None = None, error=None):
        self.id = response_id
        self.status = status
        self.output_text = output_text
        self.error = error


class FakeResponses:
    def __init__(
        self, create_response: FakeResponse, retrieve_response: FakeResponse | None = None
    ):
        self._create_response = create_response
        self._retrieve_response = retrieve_response
        self.create_calls = []
        self.retrieve_calls = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return self._create_response

    def retrieve(self, response_id):
        self.retrieve_calls.append(response_id)
        return self._retrieve_response


class FakeAgentClient:
    def __init__(
        self, create_response: FakeResponse, retrieve_response: FakeResponse | None = None
    ):
        self.responses = FakeResponses(create_response, retrieve_response)


def test_start_message_uses_background_and_store():
    fake_client = FakeAgentClient(FakeResponse("resp-001", "queued"))
    service = ChatService(agent_client=fake_client)

    job = service.start_message("What's the remote work policy?")

    assert fake_client.responses.create_calls[0]["background"] is True
    assert fake_client.responses.create_calls[0]["store"] is True
    assert job.response_id == "resp-001"
    assert job.status == "queued"
    assert job.reply is None


def test_start_message_omits_previous_response_id_when_none():
    # The API rejects an explicit `previous_response_id: null` on the first
    # message of a conversation - the key must be absent, not None.
    fake_client = FakeAgentClient(FakeResponse("resp-002", "queued"))
    service = ChatService(agent_client=fake_client)

    service.start_message("hello")

    assert fake_client.responses.create_calls[0]["input"] == "hello"
    assert "previous_response_id" not in fake_client.responses.create_calls[0]


def test_start_message_threads_previous_response_id():
    fake_client = FakeAgentClient(FakeResponse("resp-004", "queued"))
    service = ChatService(agent_client=fake_client)

    service.start_message("and what about part-time staff?", previous_response_id="resp-003")

    assert fake_client.responses.create_calls[0]["previous_response_id"] == "resp-003"


def test_get_message_status_returns_reply_when_completed():
    fake_client = FakeAgentClient(
        create_response=FakeResponse("resp-005", "queued"),
        retrieve_response=FakeResponse(
            "resp-005", "completed", output_text="The office is in Melbourne."
        ),
    )
    service = ChatService(agent_client=fake_client)

    job = service.get_message_status("resp-005")

    assert job.status == "completed"
    assert job.reply == "The office is in Melbourne."
    assert job.error is None
    assert fake_client.responses.retrieve_calls == ["resp-005"]


def test_get_message_status_returns_in_progress_without_reply():
    fake_client = FakeAgentClient(
        create_response=FakeResponse("resp-006", "queued"),
        retrieve_response=FakeResponse("resp-006", "in_progress"),
    )
    service = ChatService(agent_client=fake_client)

    job = service.get_message_status("resp-006")

    assert job.status == "in_progress"
    assert job.reply is None
    assert job.error is None


def test_get_message_status_returns_error_on_failure():
    fake_client = FakeAgentClient(
        create_response=FakeResponse("resp-007", "queued"),
        retrieve_response=FakeResponse("resp-007", "failed", error="rate limited"),
    )
    service = ChatService(agent_client=fake_client)

    job = service.get_message_status("resp-007")

    assert job.status == "failed"
    assert job.reply is None
    assert job.error == "rate limited"
