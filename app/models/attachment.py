from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Attachment(BaseModel):
    __tablename__ = "attachments"
    lead_id = Column(ForeignKey("leads.id"), nullable=False)
    lead = relationship("Lead", backref="attachments")
    filename = Column(String(255))
    content_type = Column(String(80))
    size = Column(Integer)
