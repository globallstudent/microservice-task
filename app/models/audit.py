from sqlalchemy import Column, String, ForeignKey
from app.models.base import BaseModel

class Audit(BaseModel):
    __tablename__ = "audits"
    user_id = Column(ForeignKey("users.id"), nullable=False)
    endpoint = Column(String(255), nullable=False)
    payload_hash = Column(String(128), nullable=False)
