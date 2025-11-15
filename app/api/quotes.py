from fastapi import APIRouter
from app.schemas.quote import QuoteRequest, QuoteResponse
from app.services.pricing import calculate_price
from app.core.redis import get_redis
from app.core.config import settings
import json, hashlib

router = APIRouter(prefix="/quotes", tags=["quotes"])

def _cache_key(req: QuoteRequest) -> str:
    s = json.dumps(req.model_dump(), sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()

@router.post("/calc", response_model=QuoteResponse)
async def calc_quote(req: QuoteRequest):
    key = _cache_key(req)
    redis = get_redis()
    if redis is not None:
        cached = await redis.get(f"price:{key}")
        if cached:
            obj = json.loads(cached)
            return QuoteResponse(final_price=obj["final_price"], price_breakdown=obj["price_breakdown"])

    res = await calculate_price(req)

    if redis is not None:
        try:
            await redis.set(f"price:{key}", json.dumps({"final_price": res.final_price, "price_breakdown": res.price_breakdown}, default=str), ex=settings.PRICE_CACHE_TTL)
        except Exception:
            pass

    return res
