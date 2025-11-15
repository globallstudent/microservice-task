from pydantic import BaseModel

class QuoteRequest(BaseModel):
    base_price: float
    distance_km: float
    vehicle_type: str
    season_bonus: float = 0.0
    operable: bool = True

class QuoteResponse(BaseModel):
    final_price: float
    price_breakdown: dict
