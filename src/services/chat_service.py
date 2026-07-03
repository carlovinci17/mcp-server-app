from src.models.chat import ChatJobStatus

_TERMINAL_ERROR_STATUSES = {"failed", "cancelled", "incomplete"}


class ChatService:
    def __init__(self, agent_client):
        self._client = agent_client

    def start_message(self, message: str, previous_response_id: str | None = None) -> ChatJobStatus:
        # agent_client comes from AIProjectClient.get_openai_client(agent_name=...), which
        # is already scoped to the pre-configured agent (its instructions, model, and MCP
        # tool connection) — no `model=` argument needed here.
        #
        # background=True avoids Azure Static Web Apps' hard 45-second backend request
        # timeout: a synchronous call can run well past a minute for questions that chain
        # several tool calls (confirmed - a real request took 54s). Instead this kicks the
        # run off and returns immediately; the frontend polls get_message_status() until
        # it finishes, so no single HTTP round-trip ever approaches the timeout. store=True
        # is required by the API for background responses - stateless requests are rejected.
        #
        # The API rejects an explicit `previous_response_id: null` on the first message
        # of a conversation ("Value is null but should be string") - the field must be
        # omitted entirely rather than passed as None.
        kwargs = {"input": message, "background": True, "store": True}
        if previous_response_id is not None:
            kwargs["previous_response_id"] = previous_response_id

        response = self._client.responses.create(**kwargs)
        return self._to_job_status(response)

    def get_message_status(self, response_id: str) -> ChatJobStatus:
        response = self._client.responses.retrieve(response_id)
        return self._to_job_status(response)

    def _to_job_status(self, response) -> ChatJobStatus:
        status = response.status
        if status == "completed":
            return ChatJobStatus(response_id=response.id, status=status, reply=response.output_text)
        if status in _TERMINAL_ERROR_STATUSES:
            error = getattr(response, "error", None)
            return ChatJobStatus(
                response_id=response.id,
                status=status,
                error=str(error) if error else "The request did not complete successfully.",
            )
        # queued / in_progress
        return ChatJobStatus(response_id=response.id, status=status)
