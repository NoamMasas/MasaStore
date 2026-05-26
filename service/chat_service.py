import os

from openai import AsyncOpenAI, OpenAIError

from config.config import Config
from exceptions.exception import (
    chat_service_unavailable_exception,
    session_limit_exception,
)
from model.chat_request import ChatRequest
from model.chat_response import ChatResponse
from model.user_response import UserResponse
from repository import cache_repository, item_repository

config = Config()
# Explicit api_key so import doesn't fail when OPENAI_API_KEY is unset.
client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

PROMPT_LIMIT = 5
COUNTER_KEY_TEMPLATE = "chat:user:{user_id}:count"

_PROMPT_PATH = os.path.join("resources", "prompts", "chat_system.txt")
with open(_PROMPT_PATH, encoding="utf-8") as _f:
    SYSTEM_PROMPT_TEMPLATE = _f.read()


def _build_counter_key(user_id: int) -> str:
    return COUNTER_KEY_TEMPLATE.format(user_id=user_id)


async def send_chat(request: ChatRequest, auth_user: UserResponse) -> ChatResponse:
    key = _build_counter_key(auth_user.id)

    count = cache_repository.get_counter(key)
    if count >= PROMPT_LIMIT:
        raise session_limit_exception()

    items = await item_repository.get_all_items()
    items_text = "\n".join(
        f"- {item.item_name}: ${item.price} "
        f"({'out of stock' if item.stock == 0 else f'{item.stock} in stock'})"
        for item in items
    )

    system_content = SYSTEM_PROMPT_TEMPLATE.format(product_list=items_text)
    messages = [
        {"role": "system", "content": system_content},
        *[{"role": m.role, "content": m.content} for m in request.history],
        {"role": "user", "content": request.user_message},
    ]

    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.5,
        )
    except OpenAIError:
        # Any OpenAI error (auth/rate/timeout/5xx) surfaces as 503.
        raise chat_service_unavailable_exception()

    assistant_message = response.choices[0].message.content

    new_count = cache_repository.increment_counter(key)

    return ChatResponse(
        assistant_message=assistant_message,
        prompts_left=PROMPT_LIMIT - new_count,
    )


async def reset_chat(auth_user: UserResponse):
    key = _build_counter_key(auth_user.id)
    cache_repository.reset_counter(key)
