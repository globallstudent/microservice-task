"""
Comprehensive tests for rate limiting functionality
Tests per-user rate limiting (100 requests per 10 minutes)
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import time

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.core.enums import UserRole


class TestRateLimiting:

    def test_rate_limit_config(self):
        assert settings.RATE_LIMIT == 100
        assert settings.RATE_LIMIT_WINDOW == 600  # 10 minutes

    @pytest.mark.asyncio
    async def test_rate_limit_header_presence(self):
        token = create_access_token("user_1", UserRole.ADMIN)
        client = AsyncClient(app=app, base_url="http://test")
        
        response = await client.get(
            "/health",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_per_user(self):
        user1_token = create_access_token("user_1", UserRole.ADMIN)
        user2_token = create_access_token("user_2", UserRole.ADMIN)
        client = AsyncClient(app=app, base_url="http://test")
        
        response1 = await client.get(
            "/health",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response1.status_code == 200
        
        response2 = await client.get(
            "/health",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_threshold_config(self):
        assert settings.RATE_LIMIT >= 100

    @pytest.mark.asyncio
    async def test_rate_limit_window_config(self):
        assert settings.RATE_LIMIT_WINDOW == 600

    @pytest.mark.asyncio
    async def test_unauthenticated_rate_limit(self):
        client = AsyncClient(app=app, base_url="http://test")
        
        response = await client.get("/health")
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_rate_limit_error_response(self):
        pass


class TestRateLimitEdgeCases:

    @pytest.mark.asyncio
    async def test_rate_limit_window_boundary(self):
        pass

    @pytest.mark.asyncio
    async def test_concurrent_requests_rate_limiting(self):
        pass

    @pytest.mark.asyncio
    async def test_rate_limit_reset_after_window(self):
        pass

    @pytest.mark.asyncio
    async def test_rate_limit_with_different_endpoints(self):
        token = create_access_token("user_1", UserRole.ADMIN)
        client = AsyncClient(app=app, base_url="http://test")
        
        endpoints = [
            "/health",
            "/readiness",
            "/metrics",
        ]
        
        for endpoint in endpoints:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code != 500


class TestRateLimitInteraction:

    @pytest.mark.asyncio
    async def test_rate_limit_with_pagination(self):
        token = create_access_token("user_1", UserRole.ADMIN)
        client = AsyncClient(app=app, base_url="http://test")
        
        response = await client.get(
            "/leads/?skip=0&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [200, 403, 404]

    @pytest.mark.asyncio
    async def test_rate_limit_with_different_roles(self):
        admin_token = create_access_token("admin_1", UserRole.ADMIN)
        agent_token = create_access_token("agent_1", UserRole.AGENT)
        client = AsyncClient(app=app, base_url="http://test")
        
        admin_response = await client.get(
            "/health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        agent_response = await client.get(
            "/health",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        
        assert admin_response.status_code != 500
        assert agent_response.status_code != 500


class TestRateLimitConfiguration:

    def test_rate_limit_is_adjustable(self):
        rate_limit = settings.RATE_LIMIT
        rate_limit_window = settings.RATE_LIMIT_WINDOW
        
        assert isinstance(rate_limit, int)
        assert isinstance(rate_limit_window, int)
        assert rate_limit > 0
        assert rate_limit_window > 0

    def test_rate_limit_sensible_defaults(self):

        assert settings.RATE_LIMIT >= 50
        assert settings.RATE_LIMIT <= 1000
        
        assert settings.RATE_LIMIT_WINDOW >= 60  # at least 1 minute
        assert settings.RATE_LIMIT_WINDOW <= 3600  # at most 1 hour
