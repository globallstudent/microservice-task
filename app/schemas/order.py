from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class OrderCreate(BaseModel):
    lead_id: int
    base_price: float
    notes: Optional[str] = None

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    final_price: Optional[float] = None
    notes: Optional[str] = None

class OrderOut(BaseModel):
    id: int
    lead_id: int
    status: str
    base_price: float
    final_price: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
