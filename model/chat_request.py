from typing import List, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=300)
    # Bounded to cap LLM token cost per request.
    history: List[ChatMessage] = Field(default=[], max_items=10)
