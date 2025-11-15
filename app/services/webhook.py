import httpx
import asyncio
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_webhook(payload: dict, retries: int | None = None) -> bool:

    if retries is None:
        retries = settings.WEBHOOK_RETRIES
    
    backoff = 1.0
    
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
                response = await client.post(settings.WEBHOOK_URL, json=payload)
                
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook delivery succeeded for order {payload.get('order_id')}")
                    return True
                else:
                    logger.warning(
                        f"Webhook delivery failed (attempt {attempt}/{retries}): "
                        f"Status {response.status_code} for order {payload.get('order_id')}"
                    )
        except httpx.TimeoutException:
            logger.warning(
                f"Webhook timeout (attempt {attempt}/{retries}) for order {payload.get('order_id')}"
            )
        except Exception as e:
            logger.warning(
                f"Webhook delivery error (attempt {attempt}/{retries}): {e} "
                f"for order {payload.get('order_id')}"
            )
        
        if attempt < retries:
            await asyncio.sleep(backoff)
            backoff *= 2.0
    
    logger.error(f"Webhook delivery failed after {retries} attempts for order {payload.get('order_id')}")
    return False
