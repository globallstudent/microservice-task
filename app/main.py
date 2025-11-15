from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from app.api import auth, leads, orders, quotes
from app.core.redis import init_redis, close_redis, get_redis
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")
    
    logger.info("Initializing Redis connection...")
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}. Continuing without Redis...")
    
    yield
    
    logger.info("Application shutting down...")
    await close_redis()
    logger.info("Shutdown complete")

app = FastAPI(lifespan=lifespan, title="Pricing Microservice")

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(orders.router)
app.include_router(quotes.router)

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "pricing-microservice"
    }


