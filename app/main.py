from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import auth, leads, orders, quotes
from app.core.redis import init_redis, close_redis, get_redis
from app.core.metrics import registry, request_count, request_duration, db_connected, redis_connected, get_metrics_text
import time
import logging

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            request_count.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            request_duration.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            return response
        except Exception as exc:
            duration = time.time() - start_time
            request_count.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
            request_duration.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")
    
    logger.info("Initializing Redis connection...")
    try:
        await init_redis()
        redis_connected.set(1)
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_connected.set(0)
    
    try:
        db_connected.set(1)
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_connected.set(0)
    
    yield
    
    logger.info("Application shutting down...")
    await close_redis()
    redis_connected.set(0)
    logger.info("✓ Shutdown complete")


app = FastAPI(
    title="Car Pricing Microservice",
    description="Microservice for calculating vehicle shipping prices with webhooks",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(MetricsMiddleware)

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(orders.router)
app.include_router(quotes.router)


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    return Response(
        content=get_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@app.get("/health", tags=["monitoring"])
async def health_check():
    redis = get_redis()
    redis_healthy = redis is not None
    
    return {
        "status": "healthy",
        "service": "Car Pricing Microservice",
        "version": "1.0.0",
        "dependencies": {
            "redis": "connected" if redis_healthy else "disconnected",
            "database": "connected"
        }
    }


@app.get("/readiness", tags=["monitoring"])
async def readiness_check():
    redis = get_redis()
    redis_ready = redis is not None
    
    if not redis_ready:
        return {
            "ready": False,
            "reason": "Redis not available"
        }, 503
    
    return {
        "ready": True,
        "service": "Car Pricing Microservice"
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Car Pricing Microservice",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


