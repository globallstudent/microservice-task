"""Pricing quote endpoint with Redis caching"""
import json
import hashlib
import logging
from fastapi import APIRouter

from app.schemas.quote import QuoteRequest, QuoteResponse
from app.services.pricing import calculate_price
from app.core.redis import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quotes", tags=["quotes"])


def _generate_cache_key(req: QuoteRequest) -> str:
    params_str = json.dumps(req.model_dump(), sort_keys=True)
    return f"price:{hashlib.sha256(params_str.encode()).hexdigest()}"


@router.post("/calc", response_model=QuoteResponse)
async def calc_quote(req: QuoteRequest):

    cache_key = _generate_cache_key(req)
    redis = get_redis()
    
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                obj = json.loads(cached)
                return QuoteResponse(
                    final_price=obj["final_price"],
                    price_breakdown=obj["price_breakdown"]
                )
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
    
    result = await calculate_price(req)
    
    if redis is not None:
        try:
            cache_data = {
                "final_price": result.final_price,
                "price_breakdown": result.price_breakdown
            }
            await redis.set(
                cache_key,
                json.dumps(cache_data, default=str),
                ex=settings.PRICE_CACHE_TTL
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    return result
