import os
from datetime import datetime
from typing import List, Tuple

from openai import AsyncOpenAI, OpenAIError

from config.config import Config
from exceptions.exception import (
    chat_service_unavailable_exception,
    daily_chat_limit_exception,
    session_limit_exception,
)
from model.chat_request import ChatRequest
from model.chat_response import ChatResponse
from model.user_response import UserResponse
from repository import cache_repository, item_repository

config = Config()
# Explicit api_key so import doesn't fail when GEMINI_API_KEY is unset.
client = AsyncOpenAI(api_key=config.GEMINI_API_KEY, base_url=config.GEMINI_BASE_URL)

PROMPT_LIMIT = 5
COUNTER_KEY_TEMPLATE = "chat:user:{user_id}:count"
DAILY_USER_KEY_TEMPLATE = "chat:daily:{day}:user:{user_id}"
DAILY_GLOBAL_KEY_TEMPLATE = "chat:daily:{day}:global"
DAILY_KEY_TTL_SECONDS = 2 * 24 * 60 * 60

_PROMPT_PATH = os.path.join("resources", "prompts", "chat_system.txt")
with open(_PROMPT_PATH, encoding="utf-8") as _f:
    SYSTEM_PROMPT_TEMPLATE = _f.read()


def _build_counter_key(user_id: int) -> str:
    return COUNTER_KEY_TEMPLATE.format(user_id=user_id)


def _build_daily_keys(user_id: int) -> List[Tuple[str, int]]:
    # Separate from the session counter so /chat/reset/ can't clear them.
    day = datetime.utcnow().strftime("%Y%m%d")
    caps = [
        (DAILY_USER_KEY_TEMPLATE.format(day=day, user_id=user_id), config.CHAT_DAILY_USER_LIMIT),
        (DAILY_GLOBAL_KEY_TEMPLATE.format(day=day), config.CHAT_DAILY_GLOBAL_LIMIT),
    ]
    return [(key, limit) for key, limit in caps if limit > 0]


async def send_chat(request: ChatRequest, auth_user: UserResponse) -> ChatResponse:
    key = _build_counter_key(auth_user.id)

    count = cache_repository.get_counter(key)
    if count >= PROMPT_LIMIT:
        raise session_limit_exception()

    daily_keys = _build_daily_keys(auth_user.id)
    for daily_key, limit in daily_keys:
        if cache_repository.get_counter(daily_key) >= limit:
            raise daily_chat_limit_exception()

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
            model=config.GEMINI_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.5,
        )
    except OpenAIError:
        # Any API error (auth/rate/timeout/5xx) surfaces as 503.
        raise chat_service_unavailable_exception()

    assistant_message = response.choices[0].message.content

    new_count = cache_repository.increment_counter(key)
    for daily_key, _ in daily_keys:
        cache_repository.increment_counter_with_ttl(daily_key, DAILY_KEY_TTL_SECONDS)

    return ChatResponse(
        assistant_message=assistant_message,
        prompts_left=PROMPT_LIMIT - new_count,
    )


async def reset_chat(auth_user: UserResponse):
    key = _build_counter_key(auth_user.id)
    cache_repository.reset_counter(key)
