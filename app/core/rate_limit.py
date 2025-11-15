from fastapi import HTTPException
from app.core.redis import get_redis
from app.core.config import settings

async def check_rate_limit(user_id: int):
    redis = get_redis()
    key = f"rl:{user_id}"
    current = await redis.get(key)
    if current is None:
        await redis.set(key, "1", ex=settings.RATE_LIMIT_WINDOW)
        return
    count = int(current)
    if count >= settings.RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    await redis.incr(key)
