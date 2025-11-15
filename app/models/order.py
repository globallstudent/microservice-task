from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Order(BaseModel):
    __tablename__ = "orders"
    lead_id = Column(ForeignKey("leads.id"), nullable=False)
    lead = relationship("Lead", backref="orders")
    status = Column(String(20), default="draft")
    base_price = Column(Float, nullable=False)
    final_price = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
