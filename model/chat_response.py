from pydantic import BaseModel


class ChatResponse(BaseModel):
    assistant_message: str
    prompts_left: int
