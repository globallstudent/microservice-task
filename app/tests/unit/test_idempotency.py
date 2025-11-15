import pytest
from app.utils.idempotency import get_idempotent, set_idempotent
from app.core.redis import init_redis, redis
import asyncio

@pytest.mark.asyncio
async def test_idemp_flow():
    await init_redis()
    key = "pytest-idemp"
    await redis.delete(f"idemp:{key}")
    assert await get_idempotent(key) is None
    await set_idempotent(key, {"ok": True})
    found = await get_idempotent(key)
    assert found == {"ok": True}
    await redis.delete(f"idemp:{key}")
