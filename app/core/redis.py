import logging
from typing import Optional
from redis.asyncio import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)

redis: Optional[Redis] = None

async def init_redis() -> Redis:
    global redis
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
        await redis.ping()
        logger.info("Connected to Redis")
        return redis
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

async def close_redis():
    global redis
    if redis:
        await redis.close()
        redis = None

def get_redis() -> Redis:
    global redis
    if redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis
