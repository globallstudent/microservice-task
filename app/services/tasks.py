from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND,
)
celery_app.conf.task_routes = {"app.services.tasks.reprice_order": {"queue": "reprice"}}

@celery_app.task(bind=True, max_retries=3)
def reprice_order(self, order_id: int):
    import asyncio
    from app.services.tasks_internal import reprice_order_async
    
    try:
        asyncio.run(reprice_order_async(order_id))
    except Exception as e:
        retry_kwargs = {"countdown": 2 ** self.request.retries}
        raise self.retry(exc=e, **retry_kwargs)
