from typing import cast
import redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL)


def get_redis() -> redis.Redis:
    return cast(redis.Redis, redis_client)
