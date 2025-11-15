from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str
    
    REDIS_URL: str
    
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    RATE_LIMIT: int = 100
    RATE_LIMIT_WINDOW: int = 600  # 10 minutes
    
    IDEMPOTENCY_TTL: int = 300  # 5 minutes
    PRICE_CACHE_TTL: int = 60   # 60 seconds
    
    WEBHOOK_URL: str
    WEBHOOK_TIMEOUT: int = 10
    WEBHOOK_RETRIES: int = 3
    
    CELERY_BROKER_URL: str
    CELERY_BACKEND: str
    
    API_TITLE: str = "Car Pricing Microservice"
    API_DESCRIPTION: str = "RESTful API for managing car pricing, leads, and orders"
    API_VERSION: str = "1.0.0"
    
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
