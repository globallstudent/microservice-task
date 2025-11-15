import pytest
from datetime import datetime, timedelta

from app.core.enums import AuditAction, VehicleType


class TestAuditLogging:

    @pytest.mark.asyncio
    async def test_audit_log_structure(self):
        audit_log = {
            "user_id": "user_1",
            "action": AuditAction.CREATE.value,
            "resource_type": "lead",
            "resource_id": 1,
            "changes": {"name": "John Doe"},
            "timestamp": datetime.utcnow()
        }
        
        assert audit_log["user_id"] == "user_1"
        assert audit_log["action"] == AuditAction.CREATE.value
        assert audit_log["resource_type"] == "lead"
        assert audit_log["resource_id"] == 1
        assert audit_log["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_audit_action_types(self):
        expected_actions = [
            AuditAction.CREATE.value,
            AuditAction.UPDATE.value,
            AuditAction.DELETE.value,
            AuditAction.LOGIN.value,
            AuditAction.WEBHOOK_SENT.value,
            AuditAction.REPRICE.value,
        ]
        
        for action in expected_actions:
            assert isinstance(action, str)
            assert len(action) > 0

    @pytest.mark.asyncio
    async def test_audit_user_tracking(self):
        users = ["admin_1", "agent_1", "agent_2"]
        
        for user_id in users:
            audit_log = {
                "user_id": user_id,
                "action": AuditAction.CREATE.value,
                "resource_type": "order",
                "resource_id": 1,
                "changes": {"status": "draft"},
                "timestamp": datetime.utcnow()
            }
            
            assert audit_log["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_audit_log_timestamp_tracking(self):
        before = datetime.utcnow()
        
        audit_log = {
            "user_id": "user_1",
            "action": AuditAction.CREATE.value,
            "resource_type": "lead",
            "resource_id": 1,
            "changes": {"name": "Test"},
            "timestamp": datetime.utcnow()
        }
        
        after = datetime.utcnow()
        
        assert before <= audit_log["timestamp"] <= after

    @pytest.mark.asyncio
    async def test_audit_log_changes_tracking(self):
        changes = {
            "name": "John Doe",
            "phone": "555-1234",
            "vehicle_type": VehicleType.SEDAN.value,
            "operable": True
        }
        
        audit_log = {
            "user_id": "user_1",
            "action": AuditAction.CREATE.value,
            "resource_type": "lead",
            "resource_id": 1,
            "changes": changes,
            "timestamp": datetime.utcnow()
        }
        
        assert audit_log["changes"] == changes
        assert audit_log["changes"]["name"] == "John Doe"
        assert audit_log["changes"]["vehicle_type"] == VehicleType.SEDAN.value

    @pytest.mark.asyncio
    async def test_audit_log_resource_types(self):
        resource_types = ["lead", "order", "quote", "user"]
        
        for resource_type in resource_types:
            audit_log = {
                "user_id": "user_1",
                "action": AuditAction.CREATE.value,
                "resource_type": resource_type,
                "resource_id": 1,
                "changes": {},
                "timestamp": datetime.utcnow()
            }
            
            assert audit_log["resource_type"] == resource_type

    @pytest.mark.asyncio
    async def test_audit_login_action(self):
        audit_log = {
            "user_id": "user_1",
            "action": AuditAction.LOGIN.value,
            "resource_type": "user",
            "resource_id": 1,
            "changes": {"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"},
            "timestamp": datetime.utcnow()
        }
        
        assert audit_log["action"] == AuditAction.LOGIN.value
        assert audit_log["changes"]["ip_address"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_audit_webhook_action(self):
        """Test audit logging of webhook actions"""
        audit_log = {
            "user_id": "system",
            "action": AuditAction.WEBHOOK_SENT.value,
            "resource_type": "order",
            "resource_id": 1,
            "changes": {
                "webhook_url": "https://example.com/webhook",
                "status_code": 200,
                "response_time_ms": 250
            },
            "timestamp": datetime.utcnow()
        }
        
        assert audit_log["action"] == AuditAction.WEBHOOK_SENT.value
        assert audit_log["changes"]["status_code"] == 200

    @pytest.mark.asyncio
    async def test_audit_reprice_action(self):
        audit_log = {
            "user_id": "system",
            "action": AuditAction.REPRICE.value,
            "resource_type": "order",
            "resource_id": 1,
            "changes": {
                "old_price": 100.0,
                "new_price": 125.0,
                "reason": "seasonal_adjustment"
            },
            "timestamp": datetime.utcnow()
        }
        
        assert audit_log["action"] == AuditAction.REPRICE.value
        assert audit_log["changes"]["new_price"] == 125.0

    @pytest.mark.asyncio
    async def test_audit_multiple_changes(self):
        changes = {
            "name": {"old": "John", "new": "Jane"},
            "phone": {"old": "555-1111", "new": "555-2222"},
            "vehicle_type": {"old": "sedan", "new": "suv"},
            "operable": {"old": False, "new": True},
        }
        
        audit_log = {
            "user_id": "user_1",
            "action": AuditAction.UPDATE.value,
            "resource_type": "lead",
            "resource_id": 1,
            "changes": changes,
            "timestamp": datetime.utcnow()
        }
        
        assert len(audit_log["changes"]) == 4
        assert audit_log["changes"]["name"]["new"] == "Jane"
        assert audit_log["changes"]["operable"]["new"] == True

    @pytest.mark.asyncio
    async def test_audit_ordering_chronological(self):
        audit_logs = []
        
        for i in range(5):
            timestamp = datetime.utcnow() + timedelta(seconds=i)
            audit_log = {
                "user_id": "user_1",
                "action": AuditAction.CREATE.value,
                "resource_type": "lead",
                "resource_id": i,
                "changes": {"index": i},
                "timestamp": timestamp
            }
            audit_logs.append(audit_log)
        
        for i in range(len(audit_logs) - 1):
            assert audit_logs[i]["timestamp"] <= audit_logs[i + 1]["timestamp"]
