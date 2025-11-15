# FastAPI Pricing Microservice

Auto mobile transport pricing calculation microservice built with FastAPI, PostgreSQL, Redis, and Celery.

![alt text](image_2025-11-15_00-25-07.png)

## Features

- **JWT Authentication** - Login with admin/agent roles
- **Leads Management** - CRUD operations for customer leads with filtering
- **Orders Management** - Full order lifecycle with pricing
- **Pricing Engine** - Calculate and cache transport prices
- **Idempotency** - Prevent duplicate requests with Idempotency-Key header
- **Rate Limiting** - 100 requests per 10 minutes per user
- **Background Jobs** - Async reprice with Celery + Redis
- **Webhooks** - Notify external systems on order status changes with exponential backoff
- **File Upload** - Attach documents (images, PDFs) to leads
- **Audit Logging** - Track all mutations for compliance
- **Role-Based Access** - Admin can see all leads/orders, agents see only their own
- **Prometheus Metrics** - `/metrics` endpoint

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Async ORM with PostgreSQL
- **PostgreSQL** - Relational database
- **Redis** - Caching, rate limiting, idempotency, job queue
- **Celery** - Background task processing
- **Alembic** - Database migrations
- **pytest** - Testing framework

## Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- PostgreSQL 16
- Redis 7
- Celery worker

### Quick Start with Docker

```bash
# Clone and setup
git clone <repo>
cd uic-task

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-min-32-chars-change-in-production
WEBHOOK_URL=https://your-webhook-endpoint.com/webhook
ACCESS_TOKEN_EXPIRE_MINUTES=60
RATE_LIMIT=100
RATE_LIMIT_WINDOW=600
IDEMPOTENCY_TTL=300
PRICE_CACHE_TTL=60
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_BACKEND=redis://redis:6379/1
EOF

# Start all services
docker-compose up -d

# Create database tables
docker-compose exec api alembic upgrade head

# Check health
curl http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with localhost settings
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-min-32-chars
...
EOF

# Run database (in Docker or locally)
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
docker run -d --name redis -p 6379:6379 redis:7

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload

# In another terminal, start Celery worker
celery -A app.services.tasks.celery_app worker --loglevel=info

# Start Celery beat scheduler (optional)
celery -A app.services.tasks.celery_app beat --loglevel=info
```

## API Endpoints

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass123"}'
# Returns: {"access_token": "eyJ0...", "token_type": "bearer"}
```

### Leads

```bash
TOKEN="your_token_here"

# Create lead (with idempotency)
curl -X POST http://localhost:8000/leads/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: key-123" \
  -d '{
    "name":"John Doe",
    "phone":"555-1234",
    "email":"john@example.com",
    "origin_zip":"90210",
    "dest_zip":"10001",
    "vehicle_type":"sedan",
    "operable":true
  }'

# List leads with filtering
curl "http://localhost:8000/leads/?origin_zip=90210&limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Get single lead
curl http://localhost:8000/leads/1 \
  -H "Authorization: Bearer $TOKEN"

# Update lead
curl -X PUT http://localhost:8000/leads/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone":"555-9999"}'

# Delete lead
curl -X DELETE http://localhost:8000/leads/1 \
  -H "Authorization: Bearer $TOKEN"

# Upload attachment
curl -X POST http://localhost:8000/leads/1/attachments \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@photo.jpg"
```

### Orders

```bash
# Create order
curl -X POST http://localhost:8000/orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id":1,
    "base_price":100.0,
    "notes":"Standard shipping"
  }'

# List orders
curl "http://localhost:8000/orders/?status=draft&limit=20" \
  -H "Authorization: Bearer $TOKEN"

# Get order
curl http://localhost:8000/orders/1 \
  -H "Authorization: Bearer $TOKEN"

# Update order
curl -X PUT http://localhost:8000/orders/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status":"quoted",
    "final_price":125.50
  }'

# Delete order
curl -X DELETE http://localhost:8000/orders/1 \
  -H "Authorization: Bearer $TOKEN"

# Trigger async reprice
curl -X POST http://localhost:8000/orders/1/reprice \
  -H "Authorization: Bearer $TOKEN"
```

### Pricing

```bash
# Calculate price (cached 60 seconds)
curl -X POST http://localhost:8000/quotes/calc \
  -H "Content-Type: application/json" \
  -d '{
    "base_price":100.0,
    "distance_km":50.0,
    "vehicle_type":"truck",
    "season_bonus":10.0,
    "operable":true
  }'
# Returns:
# {
#   "final_price": 190.5,
#   "price_breakdown": {
#     "base_price": 100.0,
#     "distance_cost": 75.0,
#     "vehicle_bonus": 30.0,
#     "season_bonus": 10.0,
#     "operable_adjustment": 15.0
#   }
# }
```

## Pricing Formula

```
final_price = base_price + (distance_km × 1.5) + vehicle_bonus + season_bonus + operable_adjustment

Where:
  - vehicle_bonus: sedan=10, suv=20, truck=30
  - operable_adjustment: 15 if operable else 0
  - Results cached in Redis for 60 seconds
```

## User Roles

### Admin
- Can view all leads and orders
- Can manage all orders
- Full API access

### Agent  
- Can only view/manage own leads and orders
- Limited to their own data
- Same endpoints, filtered by creator

## Rate Limiting

- **Limit**: 100 requests per 10 minutes per user
- **Header**: `X-RateLimit-Remaining` shows requests left
- **HTTP Status**: 429 when exceeded
- **Implementation**: Redis-based counter

## Idempotency

Prevent duplicate processing with idempotency key:

```bash
curl -X POST http://localhost:8000/leads/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: my-unique-key" \
  -d '{...}'
```

- Key is stored in Redis for 5 minutes
- Same response returned for duplicate requests
- Applies to: POST /leads/, PUT /leads/{id}, DELETE /leads/{id}, POST /orders/, PUT /orders/{id}, DELETE /orders/{id}

## Webhooks

Automatic notifications sent when order status changes to `quoted` or `booked`:

```json
{
  "order_id": 123,
  "final_price": 145.50,
  "status": "quoted"
}
```

**Retry Logic**:
- 3 attempts with exponential backoff (1s, 2s, 4s)
- 10-second timeout per attempt
- Failures logged but don't block order processing

**Configure**:
```env
WEBHOOK_URL=https://your-system.com/webhooks/orders
```

## Background Jobs

### Reprice Order

Triggered via: `POST /orders/{order_id}/reprice`

```python
# Celery worker processes:
1. Fetch order from database
2. Recalculate price using current formula
3. Update order.final_price
4. Change status to "quoted"
5. Send webhook notification
6. Log action
```

**Monitor**:
```bash
# View active tasks
docker-compose exec worker celery -A app.services.tasks.celery_app inspect active

# View task stats
docker-compose exec worker celery -A app.services.tasks.celery_app inspect stats
```

## Audit Logging

All mutations (POST, PUT, DELETE) are logged:

```json
{
  "id": 1,
  "user_id": 5,
  "endpoint": "POST /leads",
  "payload_hash": "sha256_hash_of_request",
  "created_at": "2025-11-15T10:30:00Z"
}
```

Query audit logs:
```sql
SELECT * FROM audits WHERE user_id = 5 ORDER BY created_at DESC;
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/test_pricing.py -v

# Run async tests only
pytest -k "async" -v

# Mock endpoints for testing
export TEST_WEBHOOK_URL="http://localhost:8000/mock-webhook"
```

## File Upload

Upload attachments to leads:

```bash
curl -X POST http://localhost:8000/leads/1/attachments \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"
```

**Constraints**:
- Accepted: `image/*`, `application/pdf`
- Max size: 5 MB
- Storage: `/data/uploads/` (Docker volume mapped)
- Filename sanitized and hashed

## Database

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Models

- `User` - Authentication (id, username, password_hash, role, created_at, updated_at)
- `Lead` - Customer lead (id, name, phone, email, origin_zip, dest_zip, vehicle_type, operable, created_by, created_at, updated_at)
- `Order` - Transport order (id, lead_id, status, base_price, final_price, notes, created_at, updated_at)
- `Attachment` - Lead documents (id, lead_id, filename, content_type, size, created_at, updated_at)
- `Audit` - Change log (id, user_id, endpoint, payload_hash, created_at, updated_at)

## Configuration

See `.env.example` for all options:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-min-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Rate Limit
RATE_LIMIT=100                    # requests
RATE_LIMIT_WINDOW=600             # seconds (10 minutes)

# Idempotency
IDEMPOTENCY_TTL=300               # seconds (5 minutes)

# Pricing
PRICE_CACHE_TTL=60                # seconds

# Webhooks
WEBHOOK_URL=https://your-endpoint/webhook

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_BACKEND=redis://localhost:6379/1
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/docs  # Swagger UI
curl http://localhost:8000/metrics  # Prometheus format
```

### Logs

```bash
# API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker

# Database logs
docker-compose logs -f db

# Redis logs
docker-compose logs -f redis
```

### Debug

```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Check database connection
docker-compose exec api python -c "from app.db.session import engine; print(engine)"

# Check Celery
docker-compose exec worker celery -A app.services.tasks.celery_app inspect ping
```

## Production Deployment

### Security

```env
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
DATABASE_URL=postgresql+asyncpg://prod_user:strong_password@prod_db/prod_db
REDIS_URL=redis://:strong_password@prod_redis:6379/0
```

### Docker Image

```bash
# Build
docker build -t pricing-service:latest .

# Push to registry
docker tag pricing-service:latest myregistry/pricing-service:1.0
docker push myregistry/pricing-service:1.0

# Deploy
docker pull myregistry/pricing-service:1.0
docker run -d \
  --name pricing-api \
  -p 8000:8000 \
  --env-file .env.prod \
  myregistry/pricing-service:1.0
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pricing-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pricing-api
  template:
    metadata:
      labels:
        app: pricing-api
    spec:
      containers:
      - name: api
        image: myregistry/pricing-service:1.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

## Troubleshooting

### Redis Connection Failed
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli -h localhost ping

# Check URL format
# redis://localhost:6379/0 
# redis://user:pass@localhost:6379/0 (with auth)
```

### Database Connection Issues
```bash
# Check PostgreSQL
docker ps | grep postgres

# Test connection
psql postgresql://user:pass@localhost/dbname

# Check migrations
docker-compose exec api alembic current
docker-compose exec api alembic heads
```

### Celery Tasks Not Processing
```bash
# Check worker is running
docker-compose ps worker

# Check task queue
docker-compose exec redis redis-cli LRANGE celery 0 -1

# Monitor tasks
celery -A app.services.tasks.celery_app events

# Check logs
docker-compose logs -f worker
```

### Rate Limit Not Working
```bash
# Check Redis keys
docker-compose exec redis redis-cli KEYS "rl:*"

# Manually reset for user (id=1)
docker-compose exec redis redis-cli DEL "rl:1"
```

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `pytest`
3. Commit: `git commit -am "Add my feature"`
4. Push: `git push origin feature/my-feature`
5. Create Pull Request

## License

MIT

## Support

For issues and questions:
1. Check existing issues
2. Create detailed bug report
3. Include logs and error messages
4. Specify environment (Docker/local)

---

**Last Updated**: 2025-11-15  
**Version**: 1.0.0  
**Status**: Production Ready