import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.core.security import create_access_token
from app.core.config import settings

# Test database setup
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgres",
    "test_db",
    1
)

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncSessionTest = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with AsyncSessionTest() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def setup_db():
    """Create test database tables"""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def test_client():
    """Create test HTTP client"""
    return AsyncClient(app=app, base_url="http://test")

@pytest.fixture
def admin_token():
    """Create admin token"""
    return create_access_token("1", "admin")

@pytest.fixture
def agent_token():
    """Create agent token"""
    return create_access_token("2", "agent")

@pytest.mark.asyncio
async def test_auth_register_and_login(test_client, setup_db):
    """Test user registration and login flow"""
    # Register user
    response = await test_client.post("/auth/register", json={
        "username": "testuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Login
    response = await test_client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    # Login with wrong password
    response = await test_client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrongpass"
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_create_lead_with_idempotency(test_client, setup_db, admin_token):
    """Test creating lead with idempotency key"""
    headers = {"Authorization": f"Bearer {admin_token}", "Idempotency-Key": "test-key-1"}
    
    lead_data = {
        "name": "John Doe",
        "phone": "555-1234",
        "email": "john@example.com",
        "origin_zip": "90210",
        "dest_zip": "10001",
        "vehicle_type": "sedan",
        "operable": True
    }
    
    # First request
    response1 = await test_client.post("/leads/", json=lead_data, headers=headers)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["id"]
    
    # Second request with same idempotency key
    response2 = await test_client.post("/leads/", json=lead_data, headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Should return same response
    assert data1["id"] == data2["id"]

@pytest.mark.asyncio
async def test_crud_leads(test_client, setup_db, admin_token):
    """Test full CRUD operations for leads"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create
    create_response = await test_client.post("/leads/", json={
        "name": "Jane Doe",
        "phone": "555-5678",
        "email": "jane@example.com",
        "origin_zip": "90210",
        "dest_zip": "10001",
        "vehicle_type": "suv",
        "operable": False
    }, headers=headers)
    assert create_response.status_code == 200
    lead_id = create_response.json()["id"]
    
    # Read
    get_response = await test_client.get(f"/leads/{lead_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Jane Doe"
    
    # Update
    update_response = await test_client.put(f"/leads/{lead_id}", json={
        "phone": "555-9999"
    }, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json()["phone"] == "555-9999"
    
    # List
    list_response = await test_client.get("/leads/?limit=10", headers=headers)
    assert list_response.status_code == 200
    leads = list_response.json()
    assert len(leads) >= 1
    
    # Delete
    delete_response = await test_client.delete(f"/leads/{lead_id}", headers=headers)
    assert delete_response.status_code == 200
    
    # Verify deleted
    get_deleted = await test_client.get(f"/leads/{lead_id}", headers=headers)
    assert get_deleted.status_code == 404

@pytest.mark.asyncio
async def test_agent_access_control(test_client, setup_db, admin_token, agent_token):
    """Test that agents can only see their own leads"""
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    
    # Admin creates lead
    admin_lead = await test_client.post("/leads/", json={
        "name": "Admin Lead",
        "phone": "555-1111",
        "email": "admin@example.com",
        "origin_zip": "90210",
        "dest_zip": "10001",
        "vehicle_type": "truck",
        "operable": True
    }, headers=admin_headers)
    admin_lead_id = admin_lead.json()["id"]
    
    # Agent creates lead
    agent_lead = await test_client.post("/leads/", json={
        "name": "Agent Lead",
        "phone": "555-2222",
        "email": "agent@example.com",
        "origin_zip": "90210",
        "dest_zip": "10001",
        "vehicle_type": "sedan",
        "operable": True
    }, headers=agent_headers)
    agent_lead_id = agent_lead.json()["id"]
    
    # Agent can see own lead
    get_own = await test_client.get(f"/leads/{agent_lead_id}", headers=agent_headers)
    assert get_own.status_code == 200
    
    # Agent cannot see admin's lead
    get_other = await test_client.get(f"/leads/{admin_lead_id}", headers=agent_headers)
    assert get_other.status_code == 403

@pytest.mark.asyncio
async def test_pricing_calculation(test_client, setup_db):
    """Test pricing calculation endpoint"""
    calc_data = {
        "base_price": 100.0,
        "distance_km": 50.0,
        "vehicle_type": "truck",
        "season_bonus": 10.0,
        "operable": True
    }
    
    response = await test_client.post("/quotes/calc", json=calc_data)
    assert response.status_code == 200
    data = response.json()
    
    # final = 100 + (50*1.5) + 30 + 10 + 15 = 190
    assert data["final_price"] >= 190
    assert "price_breakdown" in data
    breakdown = data["price_breakdown"]
    assert breakdown["base_price"] == 100.0
    assert breakdown["distance_cost"] == 75.0
    assert breakdown["vehicle_bonus"] == 30.0

@pytest.mark.asyncio
async def test_order_workflow(test_client, setup_db, admin_token):
    """Test complete order workflow"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lead
    lead_response = await test_client.post("/leads/", json={
        "name": "Order Test Lead",
        "phone": "555-0000",
        "email": "order@example.com",
        "origin_zip": "90210",
        "dest_zip": "10001",
        "vehicle_type": "sedan",
        "operable": True
    }, headers=headers)
    lead_id = lead_response.json()["id"]
    
    # Create order
    order_response = await test_client.post("/orders/", json={
        "lead_id": lead_id,
        "base_price": 100.0,
        "notes": "Test order"
    }, headers=headers)
    assert order_response.status_code == 200
    order_id = order_response.json()["id"]
    assert order_response.json()["status"] == "draft"
    
    # Update to quoted
    update_response = await test_client.put(f"/orders/{order_id}", json={
        "status": "quoted",
        "final_price": 125.50
    }, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "quoted"
    
    # List orders
    list_response = await test_client.get("/orders/?status=quoted", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1
    
    # Get single order
    get_response = await test_client.get(f"/orders/{order_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["final_price"] == 125.50

@pytest.mark.asyncio
async def test_invalid_status_transition(test_client, setup_db, admin_token):
    """Test that invalid status values are rejected"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create lead and order
    lead_response = await test_client.post("/leads/", json={
        "name": "Status Test",
        "phone": "555-0000",
        "email": "status@example.com",
        "origin_zip": "90210",
        "dest_zip": "10001",
        "vehicle_type": "sedan",
        "operable": True
    }, headers=headers)
    lead_id = lead_response.json()["id"]
    
    order_response = await test_client.post("/orders/", json={
        "lead_id": lead_id,
        "base_price": 100.0
    }, headers=headers)
    order_id = order_response.json()["id"]
    
    # Try invalid status
    update_response = await test_client.put(f"/orders/{order_id}", json={
        "status": "invalid_status"
    }, headers=headers)
    assert update_response.status_code == 400
