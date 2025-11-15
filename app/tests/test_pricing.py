import pytest
from app.services.pricing import calculate_price
from app.schemas.quote import QuoteRequest

@pytest.mark.asyncio
@pytest.mark.parametrize("base,distance,vt,season,operable,expected_min", [
    (100.0, 10.0, "sedan", 0.0, True, 125.0),      # base + distance*1.5 + vehicle_bonus + operable
    (200.0, 50.0, "truck", 10.0, False, 265.0),    # base + distance*1.5 + vehicle_bonus + season
    (0.0, 0.0, "suv", 5.0, True, 50.0),            # 0 + 0 + 20 + 5 + 15
    (50.0, 30.0, "sedan", 20.0, True, 130.0),      # 50 + 45 + 10 + 20 + 15
    (10.0, 100.0, "truck", 0.0, False, 160.0),     # 10 + 150 + 30 + 0 + 0
    (500.0, 200.0, "suv", 50.0, True, 910.0),      # 500 + 300 + 20 + 50 + 15
])
async def test_pricing_formula(base, distance, vt, season, operable, expected_min):
    req = QuoteRequest(
        base_price=base,
        distance_km=distance,
        vehicle_type=vt,
        season_bonus=season,
        operable=operable
    )
    res = await calculate_price(req)
    
    assert res.final_price >= expected_min
    assert isinstance(res.final_price, float)
    
    assert "price_breakdown" in res.model_dump()
    breakdown = res.price_breakdown
    assert breakdown["base_price"] == base
    assert breakdown["distance_cost"] == distance * 1.5
    assert breakdown["season_bonus"] == season
    
    vehicle_bonus_map = {"sedan": 10.0, "suv": 20.0, "truck": 30.0}
    assert breakdown["vehicle_bonus"] == vehicle_bonus_map[vt]
    
    assert breakdown["operable_adjustment"] == (15.0 if operable else 0.0)

