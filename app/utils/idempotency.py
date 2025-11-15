import json
from app.core.redis import get_redis
from app.core.config import settings

async def get_idempotent(key: str):
    if not key:
        return None
    redis = get_redis()
    v = await redis.get(f"idemp:{key}")
    return json.loads(v) if v else None

async def set_idempotent(key: str, value: dict):
    redis = get_redis()
    await redis.set(f"idemp:{key}", json.dumps(value, default=str), ex=settings.IDEMPOTENCY_TTL)
