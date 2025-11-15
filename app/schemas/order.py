from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.core.enums import OrderStatus


class OrderCreate(BaseModel):
    lead_id: int
    base_price: float
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    final_price: Optional[float] = None
    notes: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    lead_id: int
    status: OrderStatus
    base_price: float
    final_price: Optional[float] = None
    notes: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
