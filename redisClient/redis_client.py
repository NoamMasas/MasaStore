import redis
from config.config import Config

config = Config()
redis_client = redis.StrictRedis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    decode_responses=True,
)
