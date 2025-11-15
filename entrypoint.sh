#!/bin/bash
set -e

echo "Starting Car Pricing Microservice..."

DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
for i in {1..30}; do
    if PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" > /dev/null 2>&1; then
        echo "✓ PostgreSQL is ready!"
        break
    fi
    echo "  Attempt $i/30 - PostgreSQL not ready, waiting..."
    sleep 2
done

echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
for i in {1..30}; do
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
        echo "✓ Redis is ready!"
        break
    fi
    echo "  Attempt $i/30 - Redis not ready, waiting..."
    sleep 2
done

echo "Running database migrations..."
cd /app

if [ ! -f "alembic.ini" ]; then
    echo "✗ alembic.ini not found"
    exit 1
fi

echo "Applying migrations..."
if alembic upgrade head; then
    echo "✓ Database migrations completed successfully"
else
    echo "✗ Database migrations failed"
    exit 1
fi

echo "✓ All startup checks passed!"
echo "Starting application..."
exec "$@"
