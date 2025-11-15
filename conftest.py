import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime, timedelta

from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.core.security import create_access_token
from app.core.config import settings
from app.core.enums import UserRole



@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()



TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/test_db"
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionTest = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True
)


@pytest.fixture
async def override_get_db():
    async with AsyncSessionTest() as session:
        yield session


@pytest.fixture
async def setup_db():

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_client_with_auth():
    class AuthenticatedClient:
        def __init__(self, client, token):
            self.client = client
            self.token = token
            self.headers = {"Authorization": f"Bearer {token}"}
        
        async def get(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return await self.client.get(url, **kwargs)
        
        async def post(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return await self.client.post(url, **kwargs)
        
        async def put(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return await self.client.put(url, **kwargs)
        
        async def delete(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return await self.client.delete(url, **kwargs)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = create_access_token("test_user", UserRole.ADMIN)
        yield AuthenticatedClient(client, token)


@pytest.fixture
def admin_token():
    return create_access_token("admin_1", UserRole.ADMIN)


@pytest.fixture
def admin_token_2():
    return create_access_token("admin_2", UserRole.ADMIN)


@pytest.fixture
def agent_token():
    return create_access_token("agent_1", UserRole.AGENT)


@pytest.fixture
def agent_token_2():
    return create_access_token("agent_2", UserRole.AGENT)


@pytest.fixture
def agent_token_3():
    return create_access_token("agent_3", UserRole.AGENT)


@pytest.fixture
def expired_token():
    from app.core.security import JWT_ALGORITHM
    import jwt
    
    payload = {
        "sub": "user_1",
        "role": UserRole.ADMIN.value,
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    }
    
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )



@pytest.fixture
def valid_lead_data():
    """Create valid lead data for testing"""
    return {
        "name": "John Doe",
        "phone": "555-1234",
        "email": "john@example.com",
        "origin_zip": "90210",
        "dest_zip": "10001",
        "vehicle_type": "sedan",
        "operable": True
    }


@pytest.fixture
def valid_order_data():
    return {
        "lead_id": 1,
        "base_price": 100.0,
        "notes": "Test order"
    }


@pytest.fixture
def valid_pricing_data():
    return {
        "base_price": 100.0,
        "distance_km": 50.0,
        "vehicle_type": "sedan",
        "season_bonus": 10.0,
        "operable": True
    }


@pytest.fixture
def invalid_email():
    return "not_an_email"


@pytest.fixture
def valid_idempotency_key():
    import uuid
    return str(uuid.uuid4())


@pytest.fixture
def create_lead_factory(test_client, admin_token):
    async def _create_lead(name="Test Lead", **kwargs):
        data = {
            "name": name,
            "phone": "555-0000",
            "email": f"{name.lower()}@example.com",
            "origin_zip": "90210",
            "dest_zip": "10001",
            "vehicle_type": "sedan",
            "operable": True,
        }
        data.update(kwargs)
        
        response = await test_client.post(
            "/leads/",
            json=data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        return response.json() if response.status_code == 200 else None
    
    return _create_lead


@pytest.fixture
def create_order_factory(test_client, admin_token):
    async def _create_order(lead_id, base_price=100.0, **kwargs):
        data = {
            "lead_id": lead_id,
            "base_price": base_price,
        }
        data.update(kwargs)
        
        response = await test_client.post(
            "/orders/",
            json=data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        return response.json() if response.status_code == 200 else None
    
    return _create_order


@pytest.fixture
def app_settings():
    """Return application settings"""
    return settings


@pytest.fixture
def test_config():
    """Return test-specific configuration"""
    return {
        "TEST_DATABASE_URL": TEST_DATABASE_URL,
        "RATE_LIMIT": settings.RATE_LIMIT,
        "RATE_LIMIT_WINDOW": settings.RATE_LIMIT_WINDOW,
    }



def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests related to authentication"
    )
    config.addinivalue_line(
        "markers", "crud: marks tests related to CRUD operations"
    )
    config.addinivalue_line(
        "markers", "pricing: marks tests related to pricing"
    )
    config.addinivalue_line(
        "markers", "webhooks: marks tests related to webhooks"
    )
    config.addinivalue_line(
        "markers", "rate_limit: marks tests related to rate limiting"
    )
    config.addinivalue_line(
        "markers", "audit: marks tests related to audit logging"
    )
    config.addinivalue_line(
        "markers", "idempotency: marks tests related to idempotency"
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Add extra information to test reports
    """
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call":
        rep.keywords = item.keywords


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to handle asyncio tests
    """
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture(scope="session", autouse=True)
def startup():
    print("\n" + "="*70)
    print("Starting Test Suite")
    print("="*70)
    yield
    print("\n" + "="*70)
    print("Test Suite Complete")
    print("="*70)
