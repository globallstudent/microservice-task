import httpx, asyncio
from app.core.config import settings

async def send_webhook(payload: dict, retries: int = 3) -> bool:
    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(settings.WEBHOOK_URL, json=payload)
                if 200 <= r.status_code < 300:
                    return True
        except Exception:
            pass
        await asyncio.sleep(backoff)
        backoff *= 2.0
    return False
