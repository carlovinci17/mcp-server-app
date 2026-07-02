from pydantic import BaseModel


class ChatReply(BaseModel):
    reply: str
    response_id: str
