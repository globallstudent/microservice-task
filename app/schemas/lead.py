from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LeadCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    origin_zip: str
    dest_zip: str
    vehicle_type: str
    operable: bool = True

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    origin_zip: Optional[str] = None
    dest_zip: Optional[str] = None
    vehicle_type: Optional[str] = None
    operable: Optional[bool] = None

class LeadOut(LeadCreate):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
