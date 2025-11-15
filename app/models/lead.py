from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Lead(BaseModel):
    __tablename__ = "leads"
    name = Column(String(120), nullable=False)
    phone = Column(String(40))
    email = Column(String(120))
    origin_zip = Column(String(20))
    dest_zip = Column(String(20))
    vehicle_type = Column(String(20))
    operable = Column(Boolean, default=True)
    created_by = Column(ForeignKey("users.id"), nullable=False)
    creator = relationship("User", backref="leads")
