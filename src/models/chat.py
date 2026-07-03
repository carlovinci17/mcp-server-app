from pydantic import BaseModel


class ChatJobStatus(BaseModel):
    response_id: str
    status: str
    reply: str | None = None
    error: str | None = None
