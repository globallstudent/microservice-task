# This module is deprecated. Use app.db.session instead
from app.db.session import engine, AsyncSessionLocal, get_db

__all__ = ["engine", "AsyncSessionLocal", "get_db"]

