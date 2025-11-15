"""Prometheus metrics for monitoring"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import time
from functools import wraps
from typing import Callable

registry = CollectorRegistry()

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

db_operations = Counter(
    'db_operations_total',
    'Total database operations',
    ['operation', 'table', 'status'],
    registry=registry
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['table', 'operation'],
    registry=registry
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_key'],
    registry=registry
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_key'],
    registry=registry
)

rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['user_id'],
    registry=registry
)

webhook_deliveries = Counter(
    'webhook_deliveries_total',
    'Total webhook delivery attempts',
    ['status', 'retry_count'],
    registry=registry
)

webhook_duration = Histogram(
    'webhook_delivery_duration_seconds',
    'Webhook delivery duration in seconds',
    ['status'],
    registry=registry
)

audit_logs_created = Counter(
    'audit_logs_created_total',
    'Total audit logs created',
    ['action', 'user_id'],
    registry=registry
)

active_connections = Gauge(
    'active_connections',
    'Number of active database connections',
    registry=registry
)

redis_connected = Gauge(
    'redis_connected',
    'Redis connection status (1=connected, 0=disconnected)',
    registry=registry
)

db_connected = Gauge(
    'db_connected',
    'Database connection status (1=connected, 0=disconnected)',
    registry=registry
)


def track_request(func: Callable) -> Callable:
    """Decorator to track HTTP request metrics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            # Status will be added by middleware
            return result
        except Exception as e:
            duration = time.time() - start_time
            raise
    return wrapper


def track_db_operation(operation: str, table: str):
    """Decorator to track database operation metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                db_operations.labels(
                    operation=operation,
                    table=table,
                    status='success'
                ).inc()
                db_query_duration.labels(
                    table=table,
                    operation=operation
                ).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                db_operations.labels(
                    operation=operation,
                    table=table,
                    status='error'
                ).inc()
                db_query_duration.labels(
                    table=table,
                    operation=operation
                ).observe(duration)
                raise
        return wrapper
    return decorator


def get_metrics_text() -> str:
    """Generate Prometheus metrics in text format"""
    from prometheus_client import generate_latest
    return generate_latest(registry).decode('utf-8')
