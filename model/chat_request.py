from typing import List, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=300)
    history: List[ChatMessage] = []
