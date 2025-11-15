import pytest


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, test_client):
        response = await test_client.get("/health")
        assert response.status_code == 200
