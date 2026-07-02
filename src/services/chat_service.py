from src.models.chat import ChatReply


class ChatService:
    def __init__(self, agent_client):
        self._client = agent_client

    def send_message(self, message: str, previous_response_id: str | None = None) -> ChatReply:
        # agent_client comes from AIProjectClient.get_openai_client(agent_name=...), which
        # is already scoped to the pre-configured agent (its instructions, model, and MCP
        # tool connection) — no `model=` argument needed here.
        #
        # The API rejects an explicit `previous_response_id: null` on the first message
        # of a conversation ("Value is null but should be string") - the field must be
        # omitted entirely rather than passed as None.
        kwargs = {"input": message}
        if previous_response_id is not None:
            kwargs["previous_response_id"] = previous_response_id

        response = self._client.responses.create(**kwargs)
        return ChatReply(reply=response.output_text, response_id=response.id)
