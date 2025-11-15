from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    WEBHOOK_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    RATE_LIMIT: int = 100
    RATE_LIMIT_WINDOW: int = 600
    IDEMPOTENCY_TTL: int = 300
    PRICE_CACHE_TTL: int = 60
    CELERY_BROKER_URL: str
    CELERY_BACKEND: str

    class Config:
        env_file = ".env"

settings = Settings()
