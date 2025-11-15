from sqlalchemy import Column, String, Enum
from app.models.base import BaseModel
from app.core.enums import UserRole


class User(BaseModel):
    __tablename__ = "users"
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.AGENT)
