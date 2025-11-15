import pytest
from pydantic import ValidationError
from app.services.pricing import calculate_price
from app.schemas.quote import QuoteRequest
from app.core.enums import VehicleType
import json


class TestPricingFormula:
    """Test the core pricing formula with all vehicle types"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("base,distance,vt,season,operable,expected_min", [
        (100.0, 10.0, "sedan", 0.0, True, 125.0),      # base + distance*1.5 + vehicle_bonus + operable
        (200.0, 50.0, "truck", 10.0, False, 265.0),    # base + distance*1.5 + vehicle_bonus + season
        (0.0, 0.0, "suv", 5.0, True, 50.0),            # 0 + 0 + 20 + 5 + 15
        (50.0, 30.0, "sedan", 20.0, True, 130.0),      # 50 + 45 + 10 + 20 + 15
        (10.0, 100.0, "truck", 0.0, False, 160.0),     # 10 + 150 + 30 + 0 + 0
        (500.0, 200.0, "suv", 50.0, True, 910.0),      # 500 + 300 + 20 + 50 + 15
    ])
    async def test_pricing_formula(self, base, distance, vt, season, operable, expected_min):
        """Test pricing formula with various inputs"""
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

    @pytest.mark.asyncio
    async def test_sedan_pricing(self):
        req = QuoteRequest(
            base_price=100.0,
            distance_km=50.0,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=10.0,
            operable=True
        )
        res = await calculate_price(req)
        
        # 100 + (50 * 1.5) + 10 + 10 + 15 = 100 + 75 + 10 + 10 + 15 = 210
        assert res.final_price == 210.0
        breakdown = res.price_breakdown
        assert breakdown["vehicle_bonus"] == 10.0
        assert breakdown["distance_cost"] == 75.0
        assert breakdown["operable_adjustment"] == 15.0

    @pytest.mark.asyncio
    async def test_suv_pricing(self):
        req = QuoteRequest(
            base_price=200.0,
            distance_km=100.0,
            vehicle_type=VehicleType.SUV.value,
            season_bonus=20.0,
            operable=False
        )
        res = await calculate_price(req)
        
        # 200 + (100 * 1.5) + 20 + 20 + 0 = 200 + 150 + 20 + 20 + 0 = 390
        assert res.final_price == 390.0
        breakdown = res.price_breakdown
        assert breakdown["vehicle_bonus"] == 20.0
        assert breakdown["distance_cost"] == 150.0
        assert breakdown["operable_adjustment"] == 0.0

    @pytest.mark.asyncio
    async def test_truck_pricing(self):
        """Test truck pricing specifically"""
        req = QuoteRequest(
            base_price=300.0,
            distance_km=200.0,
            vehicle_type=VehicleType.TRUCK.value,
            season_bonus=50.0,
            operable=True
        )
        res = await calculate_price(req)
        
        # 300 + (200 * 1.5) + 30 + 50 + 15 = 300 + 300 + 30 + 50 + 15 = 695
        assert res.final_price == 695.0
        breakdown = res.price_breakdown
        assert breakdown["vehicle_bonus"] == 30.0
        assert breakdown["distance_cost"] == 300.0
        assert breakdown["operable_adjustment"] == 15.0

    @pytest.mark.asyncio
    async def test_zero_values_pricing(self):
        """Test pricing with zero values"""
        req = QuoteRequest(
            base_price=0.0,
            distance_km=0.0,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=0.0,
            operable=False
        )
        res = await calculate_price(req)
        
        # 0 + 0 + 10 + 0 + 0 = 10
        assert res.final_price == 10.0

    @pytest.mark.asyncio
    async def test_high_values_pricing(self):
        """Test pricing with high values"""
        req = QuoteRequest(
            base_price=10000.0,
            distance_km=5000.0,
            vehicle_type=VehicleType.TRUCK.value,
            season_bonus=1000.0,
            operable=True
        )
        res = await calculate_price(req)
        
        # 10000 + (5000 * 1.5) + 30 + 1000 + 15 = 10000 + 7500 + 30 + 1000 + 15 = 18545
        assert res.final_price == 18545.0

    @pytest.mark.asyncio
    async def test_operable_adjustment_impact(self):
        """Test operable adjustment impact on pricing"""
        req_operable = QuoteRequest(
            base_price=100.0,
            distance_km=50.0,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=10.0,
            operable=True
        )
        res_operable = await calculate_price(req_operable)
        
        req_not_operable = QuoteRequest(
            base_price=100.0,
            distance_km=50.0,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=10.0,
            operable=False
        )
        res_not_operable = await calculate_price(req_not_operable)
        
        # Operable should be 15.0 higher
        assert res_operable.final_price - res_not_operable.final_price == 15.0

    @pytest.mark.asyncio
    async def test_distance_cost_calculation(self):
        """Test that distance cost is correctly calculated"""
        distances = [10.0, 50.0, 100.0, 1000.0]
        
        for distance in distances:
            req = QuoteRequest(
                base_price=100.0,
                distance_km=distance,
                vehicle_type=VehicleType.SEDAN.value,
                season_bonus=0.0,
                operable=False
            )
            res = await calculate_price(req)
            
            expected_distance_cost = distance * 1.5
            assert res.price_breakdown["distance_cost"] == expected_distance_cost

    @pytest.mark.asyncio
    async def test_vehicle_bonus_differences(self):
        base_price = 100.0
        distance = 50.0
        season = 10.0
        
        vehicles = [
            (VehicleType.SEDAN.value, 10.0),
            (VehicleType.SUV.value, 20.0),
            (VehicleType.TRUCK.value, 30.0)
        ]
        
        prices = []
        for vehicle_type, expected_bonus in vehicles:
            req = QuoteRequest(
                base_price=base_price,
                distance_km=distance,
                vehicle_type=vehicle_type,
                season_bonus=season,
                operable=True
            )
            res = await calculate_price(req)
            prices.append(res.final_price)
            
            assert res.price_breakdown["vehicle_bonus"] == expected_bonus
        
        assert prices[2] > prices[1] > prices[0]

class TestPriceBreakdown:

    @pytest.mark.asyncio
    async def test_breakdown_structure(self):
        """Test price breakdown has all required fields"""
        req = QuoteRequest(
            base_price=100.0,
            distance_km=50.0,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=10.0,
            operable=True
        )
        res = await calculate_price(req)
        
        breakdown = res.price_breakdown
        required_fields = [
            "base_price",
            "distance_cost",
            "vehicle_bonus",
            "season_bonus",
            "operable_adjustment"
        ]
        
        for field in required_fields:
            assert field in breakdown
            assert isinstance(breakdown[field], (int, float))

    @pytest.mark.asyncio
    async def test_breakdown_adds_to_final_price(self):
        req = QuoteRequest(
            base_price=100.0,
            distance_km=50.0,
            vehicle_type=VehicleType.SUV.value,
            season_bonus=10.0,
            operable=True
        )
        res = await calculate_price(req)
        
        breakdown = res.price_breakdown
        calculated_sum = (
            breakdown["base_price"] +
            breakdown["distance_cost"] +
            breakdown["vehicle_bonus"] +
            breakdown["season_bonus"] +
            breakdown["operable_adjustment"]
        )
        
        assert calculated_sum == res.final_price

    @pytest.mark.asyncio
    async def test_breakdown_all_positive(self):
        req = QuoteRequest(
            base_price=100.0,
            distance_km=50.0,
            vehicle_type=VehicleType.TRUCK.value,
            season_bonus=10.0,
            operable=True
        )
        res = await calculate_price(req)
        
        breakdown = res.price_breakdown
        for field, value in breakdown.items():
            assert value >= 0

class TestPricingEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_minimum_price(self):
        """Test that final price has a reasonable minimum"""
        req = QuoteRequest(
            base_price=0.0,
            distance_km=0.0,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=0.0,
            operable=False
        )
        res = await calculate_price(req)
        
        assert res.final_price >= 10.0

    @pytest.mark.asyncio
    async def test_negative_base_price_handling(self):
        req = QuoteRequest(
            base_price=-100.0,
            distance_km=50.0,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=10.0,
            operable=True
        )
        try:
            res = await calculate_price(req)
            assert isinstance(res.final_price, (int, float))
        except (ValueError, ValidationError):
            pass

    @pytest.mark.asyncio
    async def test_very_large_distance(self):
        req = QuoteRequest(
            base_price=100.0,
            distance_km=100000.0,
            vehicle_type=VehicleType.TRUCK.value,
            season_bonus=50.0,
            operable=True
        )
        res = await calculate_price(req)
        
        assert res.final_price > 0
        expected_distance_cost = 100000.0 * 1.5
        assert res.price_breakdown["distance_cost"] == expected_distance_cost

    @pytest.mark.asyncio
    async def test_decimal_values(self):
        req = QuoteRequest(
            base_price=99.99,
            distance_km=12.34,
            vehicle_type=VehicleType.SEDAN.value,
            season_bonus=5.55,
            operable=True
        )
        res = await calculate_price(req)
        
        assert res.final_price > 0
        assert res.price_breakdown["distance_cost"] == 12.34 * 1.5

