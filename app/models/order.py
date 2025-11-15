from sqlalchemy import Column, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.core.enums import OrderStatus

class Order(BaseModel):
    __tablename__ = "orders"
    
    lead_id = Column(ForeignKey("leads.id"), nullable=False)
    created_by = Column(ForeignKey("users.id"), nullable=False)
    
    lead = relationship("Lead", backref="orders")
    creator = relationship("User", backref="orders")
    
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT, nullable=False)
    base_price = Column(Float, nullable=False)
    final_price = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
