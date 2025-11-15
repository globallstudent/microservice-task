#!/bin/bash
set -e

echo "Starting Car Pricing Microservice..."

MAX_ATTEMPTS=30
ATTEMPT=1
while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} -U ${DB_USER:-postgres} > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS - PostgreSQL not ready, waiting..."
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "Failed to connect to PostgreSQL after $MAX_ATTEMPTS attempts"
    exit 1
fi

echo "Initializing Database..."
cd /app

if [ -f "alembic.ini" ]; then
    MIGRATION_FILES=$(find alembic/versions -name "*.py" -type f | grep -v __pycache__ | wc -l)
    
    if [ $MIGRATION_FILES -eq 0 ]; then
        echo "No migration files found. Running alembic revision --autogenerate -m 'init'..."
        alembic revision --autogenerate -m "init"
    else
        echo "Found $MIGRATION_FILES migration files. Skipping autogenerate."
    fi
    
    echo "Running alembic upgrade head..."
    alembic upgrade head || {
        echo "Alembic upgrade failed. Attempting downgrade and retry..."
        alembic downgrade base || true
        alembic upgrade head
    }
else
    echo "No alembic.ini found, skipping migrations"
    exit 1
fi

echo "All checks passed! Starting application..."
exec "$@"
