from app.schemas.quote import QuoteRequest, QuoteResponse
from app.core.enums import VehicleType

VEHICLE_BONUS = {
    VehicleType.SEDAN: 10.0,
    VehicleType.SUV: 20.0,
    VehicleType.TRUCK: 30.0
}
OPERABLE_ADJUSTMENT = 15.0
DISTANCE_COEFF = 1.5


async def calculate_price(req: QuoteRequest) -> QuoteResponse:

    breakdown = {
        "base_price": req.base_price,
        "distance_cost": req.distance_km * DISTANCE_COEFF,
        "vehicle_bonus": VEHICLE_BONUS.get(req.vehicle_type, 0.0),
        "season_bonus": req.season_bonus,
        "operable_adjustment": OPERABLE_ADJUSTMENT if req.operable else 0.0,
    }
    final_price = sum(breakdown.values())
    return QuoteResponse(final_price=final_price, price_breakdown=breakdown)
