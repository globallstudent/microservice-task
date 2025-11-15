from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.core.config import settings
from app.models.order import Order
from app.schemas.quote import QuoteRequest
from app.services.pricing import calculate_price
from app.services.webhook import send_webhook

engine_worker = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
AsyncSessionWorker = sessionmaker(engine_worker, class_=AsyncSession, expire_on_commit=False)

async def reprice_order_async(order_id: int):
    """Background task to reprice an order"""
    try:
        async with AsyncSessionWorker() as db:
            res = await db.execute(select(Order).where(Order.id == order_id))
            order = res.scalars().first()
            if not order:
                return
            
            # Mock: in real app fetch lead details
            quote_req = QuoteRequest(
                base_price=order.base_price,
                distance_km=100.0,
                vehicle_type="sedan",
                season_bonus=0.0,
                operable=True,
            )
            q = await calculate_price(quote_req)
            
            old_price = order.final_price
            order.final_price = q.final_price
            db.add(order)
            await db.commit()
            
            # Send webhook only if price changed
            if old_price != order.final_price:
                await send_webhook({
                    "order_id": order.id,
                    "final_price": order.final_price,
                    "old_price": old_price,
                    "status": order.status
                })
    except Exception as e:
        import logging
        logging.error(f"Reprice task failed for order {order_id}: {e}")
