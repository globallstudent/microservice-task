from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.db.session import get_db
from app.models.order import Order
from app.models.lead import Lead
from app.schemas.order import OrderCreate, OrderUpdate, OrderOut
from app.core.security import get_current_user
from app.services.tasks import reprice_order
from app.core.audit_decorator import audit_log
from app.core.rate_limit import check_rate_limit
from app.services.webhook import send_webhook
from app.core.auth_utils import check_ownership, check_not_found, filter_by_user
from app.core.response_builders import build_order_response, build_order_response_list
from app.core.enums import OrderStatus

router = APIRouter(prefix="/orders", tags=["orders"])

VALID_ORDER_STATUSES = {OrderStatus.DRAFT, OrderStatus.QUOTED, OrderStatus.BOOKED, OrderStatus.DELIVERED}


@router.post("/", response_model=OrderOut)
@audit_log("create_order")
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Lead).where(Lead.id == payload.lead_id))
    lead = res.scalars().first()
    check_not_found(lead, "Lead", payload.lead_id)
    check_ownership(lead, current_user, "Lead")
    
    order = Order(
        lead_id=payload.lead_id,
        base_price=payload.base_price,
        notes=payload.notes,
        status=OrderStatus.DRAFT,
        created_by=int(current_user.id),
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    return build_order_response(order)


@router.get("/", response_model=List[OrderOut])
async def list_orders(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    q = select(Order).options(selectinload(Order.lead))
    
    if current_user.role == "agent":
        q = q.join(Lead).where(Lead.created_by == int(current_user.id))
    
    if status:
        q = q.where(Order.status == status)
    
    q = q.limit(limit).offset(offset)
    res = await db.execute(q)
    orders = res.scalars().all()
    
    return build_order_response_list(orders)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    res = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.lead))
    )
    order = res.scalars().first()
    check_not_found(order, "Order", order_id)
    check_ownership(order.lead, current_user, "Order")
    
    return build_order_response(order)


@router.put("/{order_id}", response_model=OrderOut)
@audit_log("update_order")
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update an order"""
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.lead))
    )
    order = res.scalars().first()
    check_not_found(order, "Order", order_id)
    check_ownership(order.lead, current_user, "Order")
    
    if payload.status and payload.status not in VALID_ORDER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of {VALID_ORDER_STATUSES}"
        )
    
    old_status = order.status
    
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Trigger webhook if status changed to quoted or booked
    if old_status != order.status and order.status in [OrderStatus.QUOTED, OrderStatus.BOOKED]:
        await send_webhook({
            "order_id": order.id,
            "final_price": order.final_price or order.base_price,
            "status": order.status
        })
    
    return build_order_response(order)


@router.delete("/{order_id}")
@audit_log("delete_order")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.lead))
    )
    order = res.scalars().first()
    check_not_found(order, "Order", order_id)
    check_ownership(order.lead, current_user, "Order")
    
    await db.delete(order)
    await db.commit()
    
    return {"deleted": True}


@router.post("/{order_id}/reprice")
@audit_log("reprice_order")
async def reprice(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Order).where(Order.id == order_id))
    order = res.scalars().first()
    check_not_found(order, "Order", order_id)
    
    reprice_order.delay(order_id)
    
    return {"status": "queued"}
