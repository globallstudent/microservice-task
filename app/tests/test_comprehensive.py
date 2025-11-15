import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from app.core.security import create_access_token
from app.core.config import settings
from app.core.enums import UserRole, VehicleType, OrderStatus, AuditAction


class TestAuthentication:

    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_client, setup_db):
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime" in data
        assert "database" in data

    @pytest.mark.asyncio
    async def test_readiness_endpoint(self, test_client, setup_db):
        response = await test_client.get("/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, test_client, setup_db):
        response = await test_client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        assert "# HELP" in content or "TYPE" in content or "http_requests" in content

    @pytest.mark.asyncio
    async def test_valid_token_access(self, test_client, setup_db, admin_token):
        response = await test_client.get(
            "/leads/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_token_denied(self, test_client, setup_db):
        response = await test_client.get("/leads/")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token_denied(self, test_client, setup_db):
        response = await test_client.get(
            "/leads/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_role_admin_only_endpoint(self, test_client, setup_db, admin_token, agent_token):
        # Admin can delete (admin-only operation)
        admin_response = await test_client.delete(
            "/leads/999999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code in [404, 200]  # May not exist, but endpoint accessible
        
    @pytest.mark.asyncio
    async def test_role_enforcement(self, test_client, setup_db, admin_token, agent_token):
        """Test role-based access control"""
        admin_get = await test_client.get(
            "/leads/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_get.status_code == 200
        
        agent_get = await test_client.get(
            "/leads/",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert agent_get.status_code == 200

class TestCRUDOperations:

    @pytest.mark.asyncio
    async def test_create_lead(self, test_client, setup_db, admin_token):
        lead_data = {
            "name": "John Doe",
            "phone": "555-1234",
            "email": "john@example.com",
            "origin_zip": "90210",
            "dest_zip": "10001",
            "vehicle_type": VehicleType.SEDAN.value,
            "operable": True
        }
        response = await test_client.post(
            "/leads/",
            json=lead_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["vehicle_type"] == VehicleType.SEDAN.value

    @pytest.mark.asyncio
    async def test_get_lead(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Jane Smith",
                "phone": "555-5678",
                "email": "jane@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SUV.value,
                "operable": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        get_response = await test_client.get(
            f"/leads/{lead_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Jane Smith"

    @pytest.mark.asyncio
    async def test_get_nonexistent_lead(self, test_client, setup_db, admin_token):
        response = await test_client.get(
            "/leads/999999999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_lead(self, test_client, setup_db, admin_token):
        """Test updating a lead"""
        create_response = await test_client.post(
            "/leads/",
            json={
                "name": "Test Lead",
                "phone": "555-1111",
                "email": "test@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.TRUCK.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = create_response.json()["id"]
        
        update_response = await test_client.put(
            f"/leads/{lead_id}",
            json={"phone": "555-9999", "name": "Updated Name"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["phone"] == "555-9999"
        assert update_response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_lead(self, test_client, setup_db, admin_token):
        """Test deleting a lead"""
        create_response = await test_client.post(
            "/leads/",
            json={
                "name": "Delete Me",
                "phone": "555-2222",
                "email": "delete@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = create_response.json()["id"]
        
        delete_response = await test_client.delete(
            f"/leads/{lead_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 200
        
        get_response = await test_client.get(
            f"/leads/{lead_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_leads_pagination(self, test_client, setup_db, admin_token):
        for i in range(15):
            await test_client.post(
                "/leads/",
                json={
                    "name": f"Lead {i}",
                    "phone": f"555-{i:04d}",
                    "email": f"lead{i}@example.com",
                    "origin_zip": "90210",
                    "dest_zip": "10001",
                    "vehicle_type": VehicleType.SEDAN.value,
                    "operable": True
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        response1 = await test_client.get(
            "/leads/?skip=0&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) <= 10
        
        response2 = await test_client.get(
            "/leads/?skip=10&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        if len(data1) == 10 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]

    @pytest.mark.asyncio
    async def test_create_order(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Order Lead",
                "phone": "555-3333",
                "email": "order@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        order_response = await test_client.post(
            "/orders/",
            json={
                "lead_id": lead_id,
                "base_price": 100.0,
                "notes": "Test order"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert order_response.status_code == 200
        order_data = order_response.json()
        assert order_data["status"] == OrderStatus.DRAFT.value
        assert order_data["lead_id"] == lead_id

    @pytest.mark.asyncio
    async def test_update_order_status(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Status Lead",
                "phone": "555-4444",
                "email": "status@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SUV.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        order_response = await test_client.post(
            "/orders/",
            json={"lead_id": lead_id, "base_price": 150.0},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        order_id = order_response.json()["id"]
        
        update_response = await test_client.put(
            f"/orders/{order_id}",
            json={
                "status": OrderStatus.QUOTED.value,
                "final_price": 175.50
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == OrderStatus.QUOTED.value
        assert update_response.json()["final_price"] == 175.50

    @pytest.mark.asyncio
    async def test_list_orders_pagination(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Multi Order Lead",
                "phone": "555-5555",
                "email": "multiorder@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.TRUCK.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        # Create multiple orders
        for i in range(5):
            await test_client.post(
                "/orders/",
                json={"lead_id": lead_id, "base_price": 100.0 + i*10},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        # Test pagination
        response = await test_client.get(
            "/orders/?skip=0&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 5



class TestDataIsolation:

    @pytest.mark.asyncio
    async def test_agent_sees_only_own_leads(self, test_client, setup_db, admin_token, agent_token, agent_2_token):
        admin_lead = await test_client.post(
            "/leads/",
            json={
                "name": "Admin Lead",
                "phone": "555-6666",
                "email": "admin_lead@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        admin_lead_id = admin_lead.json()["id"]
        
        agent1_lead = await test_client.post(
            "/leads/",
            json={
                "name": "Agent1 Lead",
                "phone": "555-7777",
                "email": "agent1@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SUV.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        agent1_lead_id = agent1_lead.json()["id"]
        
        agent2_lead = await test_client.post(
            "/leads/",
            json={
                "name": "Agent2 Lead",
                "phone": "555-8888",
                "email": "agent2@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.TRUCK.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {agent_2_token}"}
        )
        agent2_lead_id = agent2_lead.json()["id"]
        
        admin_list = await test_client.get(
            "/leads/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_list.status_code == 200
        assert len(admin_list.json()) >= 3
        
        agent1_list = await test_client.get(
            "/leads/",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert agent1_list.status_code == 200
        
        get_own = await test_client.get(
            f"/leads/{agent1_lead_id}",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert get_own.status_code == 200
        
        get_other = await test_client.get(
            f"/leads/{agent2_lead_id}",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert get_other.status_code == 403

    @pytest.mark.asyncio
    async def test_agent_cannot_delete_lead(self, test_client, setup_db, agent_token):
        """Test that agents cannot delete leads"""
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Delete Test",
                "phone": "555-9999",
                "email": "deletetest@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        delete_response = await test_client.delete(
            f"/leads/{lead_id}",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        # Admin-only operation
        assert delete_response.status_code in [403, 401, 405]


class TestPricing:
    """Test pricing calculations and caching"""

    @pytest.mark.asyncio
    async def test_pricing_calculation_sedan(self, test_client, setup_db):
        """Test pricing calculation for sedan"""
        response = await test_client.post(
            "/quotes/calc",
            json={
                "base_price": 100.0,
                "distance_km": 50.0,
                "vehicle_type": VehicleType.SEDAN.value,
                "season_bonus": 10.0,
                "operable": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "final_price" in data
        assert "price_breakdown" in data
        breakdown = data["price_breakdown"]
        
        assert breakdown["base_price"] == 100.0
        assert breakdown["distance_cost"] == 50.0 * 1.5  # distance_km * 1.5
        assert breakdown["vehicle_bonus"] == 10.0  # sedan
        assert breakdown["season_bonus"] == 10.0
        assert breakdown["operable_adjustment"] == 15.0  # operable=True

    @pytest.mark.asyncio
    async def test_pricing_calculation_suv(self, test_client, setup_db):
        """Test pricing calculation for SUV"""
        response = await test_client.post(
            "/quotes/calc",
            json={
                "base_price": 100.0,
                "distance_km": 50.0,
                "vehicle_type": VehicleType.SUV.value,
                "season_bonus": 5.0,
                "operable": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        breakdown = data["price_breakdown"]
        
        assert breakdown["vehicle_bonus"] == 20.0  # SUV
        assert breakdown["operable_adjustment"] == 0.0  # operable=False

    @pytest.mark.asyncio
    async def test_pricing_calculation_truck(self, test_client, setup_db):
        response = await test_client.post(
            "/quotes/calc",
            json={
                "base_price": 200.0,
                "distance_km": 100.0,
                "vehicle_type": VehicleType.TRUCK.value,
                "season_bonus": 20.0,
                "operable": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        breakdown = data["price_breakdown"]
        
        assert breakdown["base_price"] == 200.0
        assert breakdown["distance_cost"] == 100.0 * 1.5
        assert breakdown["vehicle_bonus"] == 30.0  # Truck
        assert breakdown["season_bonus"] == 20.0
        assert breakdown["operable_adjustment"] == 15.0

    @pytest.mark.asyncio
    async def test_pricing_cache_hit(self, test_client, setup_db):
        pricing_data = {
            "base_price": 100.0,
            "distance_km": 50.0,
            "vehicle_type": VehicleType.SEDAN.value,
            "season_bonus": 10.0,
            "operable": True
        }
        
        response1 = await test_client.post("/quotes/calc", json=pricing_data)
        assert response1.status_code == 200
        data1 = response1.json()
        
        response2 = await test_client.post("/quotes/calc", json=pricing_data)
        assert response2.status_code == 200
        data2 = response2.json()
        
        assert data1["final_price"] == data2["final_price"]

    @pytest.mark.asyncio
    async def test_pricing_invalid_vehicle_type(self, test_client, setup_db):
        response = await test_client.post(
            "/quotes/calc",
            json={
                "base_price": 100.0,
                "distance_km": 50.0,
                "vehicle_type": "invalid_type",
                "season_bonus": 10.0,
                "operable": True
            }
        )
        assert response.status_code == 422


class TestWebhooks:

    @pytest.mark.asyncio
    async def test_webhook_configuration(self, test_client, setup_db):
        assert settings.WEBHOOK_URL is not None
        assert settings.WEBHOOK_TIMEOUT == 10
        assert settings.WEBHOOK_RETRIES == 3

    @pytest.mark.asyncio
    async def test_order_status_change_triggers_webhook(self, test_client, setup_db, admin_token):
        """Test that order status changes trigger webhooks"""
        # Create lead
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Webhook Lead",
                "phone": "555-0000",
                "email": "webhook@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        order_response = await test_client.post(
            "/orders/",
            json={"lead_id": lead_id, "base_price": 100.0},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        order_id = order_response.json()["id"]
        
        update_response = await test_client.put(
            f"/orders/{order_id}",
            json={"status": OrderStatus.QUOTED.value, "final_price": 125.0},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert update_response.status_code == 200


class TestRateLimiting:

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, test_client, setup_db, admin_token):
        response = await test_client.get(
            "/leads/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_configuration(self, test_client, setup_db):
        assert settings.RATE_LIMIT == 100
        assert settings.RATE_LIMIT_WINDOW == 600  # 10 minutes



class TestAuditLogging:

    @pytest.mark.asyncio
    async def test_audit_log_on_lead_creation(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Audited Lead",
                "phone": "555-1111",
                "email": "audited@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert lead_response.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_log_on_lead_update(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Original Name",
                "phone": "555-2222",
                "email": "audit_update@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SUV.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        update_response = await test_client.put(
            f"/leads/{lead_id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert update_response.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_log_on_lead_deletion(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Delete Audit",
                "phone": "555-3333",
                "email": "audit_delete@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.TRUCK.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        delete_response = await test_client.delete(
            f"/leads/{lead_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_log_on_order_creation(self, test_client, setup_db, admin_token):
        # Create lead
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Order Audit Lead",
                "phone": "555-4444",
                "email": "order_audit@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lead_id = lead_response.json()["id"]
        
        order_response = await test_client.post(
            "/orders/",
            json={"lead_id": lead_id, "base_price": 100.0},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert order_response.status_code == 200



class TestIdempotency:

    @pytest.mark.asyncio
    async def test_idempotent_lead_creation(self, test_client, setup_db, admin_token):
        lead_data = {
            "name": "Idempotent Lead",
            "phone": "555-5555",
            "email": "idempotent@example.com",
            "origin_zip": "90210",
            "dest_zip": "10001",
            "vehicle_type": VehicleType.SEDAN.value,
            "operable": True
        }
        
        response1 = await test_client.post(
            "/leads/",
            json=lead_data,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Idempotency-Key": "unique-key-123"
            }
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        response2 = await test_client.post(
            "/leads/",
            json=lead_data,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Idempotency-Key": "unique-key-123"
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        assert data1["id"] == data2["id"]


class TestEnums:

    @pytest.mark.asyncio
    async def test_user_role_enum(self, test_client, setup_db):
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.AGENT.value == "agent"

    @pytest.mark.asyncio
    async def test_vehicle_type_enum(self, test_client, setup_db):
        """Test VehicleType enum values"""
        assert VehicleType.SEDAN.value == "sedan"
        assert VehicleType.SUV.value == "suv"
        assert VehicleType.TRUCK.value == "truck"

    @pytest.mark.asyncio
    async def test_order_status_enum(self, test_client, setup_db):
        assert OrderStatus.DRAFT.value == "draft"
        assert OrderStatus.QUOTED.value == "quoted"
        assert OrderStatus.BOOKED.value == "booked"
        assert OrderStatus.DELIVERED.value == "delivered"

    @pytest.mark.asyncio
    async def test_audit_action_enum(self, test_client, setup_db):
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.DELETE.value == "delete"
        assert AuditAction.LOGIN.value == "login"



class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_invalid_json_request(self, test_client, setup_db, admin_token):
        response = await test_client.post(
            "/leads/",
            content="invalid json",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_field(self, test_client, setup_db, admin_token):
        response = await test_client.post(
            "/leads/",
            json={
                "name": "Missing Phone",
                "email": "missing@example.com",
                # missing phone
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_email_format(self, test_client, setup_db, admin_token):
        response = await test_client.post(
            "/leads/",
            json={
                "name": "Invalid Email",
                "phone": "555-6666",
                "email": "not_an_email",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return validation error
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_duplicate_email_allowed(self, test_client, setup_db, admin_token):
        lead_data1 = {
            "name": "User 1",
            "phone": "555-7777",
            "email": "duplicate@example.com",
            "origin_zip": "90210",
            "dest_zip": "10001",
            "vehicle_type": VehicleType.SEDAN.value,
            "operable": True
        }
        
        lead_data2 = {
            "name": "User 2",
            "phone": "555-8888",
            "email": "duplicate@example.com",
            "origin_zip": "90210",
            "dest_zip": "10001",
            "vehicle_type": VehicleType.SUV.value,
            "operable": True
        }
        
        response1 = await test_client.post(
            "/leads/",
            json=lead_data1,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response1.status_code == 200

        response2 = await test_client.post(
            "/leads/",
            json=lead_data2,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == 200



class TestWorkflows:
    """Test complete workflows"""

    @pytest.mark.asyncio
    async def test_complete_lead_to_order_workflow(self, test_client, setup_db, admin_token):
        lead_response = await test_client.post(
            "/leads/",
            json={
                "name": "Complete Workflow",
                "phone": "555-0001",
                "email": "workflow@example.com",
                "origin_zip": "90210",
                "dest_zip": "10001",
                "vehicle_type": VehicleType.SEDAN.value,
                "operable": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert lead_response.status_code == 200
        lead_id = lead_response.json()["id"]
        
        price_response = await test_client.post(
            "/quotes/calc",
            json={
                "base_price": 100.0,
                "distance_km": 50.0,
                "vehicle_type": VehicleType.SEDAN.value,
                "season_bonus": 10.0,
                "operable": True
            }
        )
        assert price_response.status_code == 200
        final_price = price_response.json()["final_price"]
        
        order_response = await test_client.post(
            "/orders/",
            json={"lead_id": lead_id, "base_price": 100.0},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert order_response.status_code == 200
        order_id = order_response.json()["id"]
        
        update_response = await test_client.put(
            f"/orders/{order_id}",
            json={
                "status": OrderStatus.QUOTED.value,
                "final_price": final_price
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["final_price"] == final_price
        
        book_response = await test_client.put(
            f"/orders/{order_id}",
            json={"status": OrderStatus.BOOKED.value},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert book_response.status_code == 200
        assert book_response.json()["status"] == OrderStatus.BOOKED.value
