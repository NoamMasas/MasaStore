from typing import Optional

from config.config import Config
from redisClient.redis_client import redis_client

config = Config()


def get_cache_entity(key: str) -> Optional[str]:
    if redis_client.exists(key):
        return redis_client.get(key)
    return None


def create_cache_entity(key: str, value: str):
    if not redis_client.exists(key):
        redis_client.setex(key, config.REDIS_TTL, value)


def update_cache_entity(key: str, value: str):
    if redis_client.exists(key):
        redis_client.setex(key, config.REDIS_TTL, value)


def remove_cache_entity(key: str):
    if redis_client.exists(key):
        redis_client.delete(key)


def is_key_exists(key: str) -> bool:
    return bool(redis_client.exists(key))


def get_counter(key: str) -> int:
    value = redis_client.get(key)
    return int(value) if value else 0


def increment_counter(key: str) -> int:
    return redis_client.incr(key)


def increment_counter_with_ttl(key: str, ttl_seconds: int) -> int:
    value = redis_client.incr(key)
    if value == 1:
        redis_client.expire(key, ttl_seconds)
    return value


def reset_counter(key: str):
    redis_client.delete(key)
