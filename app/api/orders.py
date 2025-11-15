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
from app.core.audit import record_audit
from app.core.rate_limit import check_rate_limit
from app.services.webhook import send_webhook

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderOut)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Lead).where(Lead.id == payload.lead_id))
    lead = res.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if current_user.role == "agent" and lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    order = Order(
        lead_id=payload.lead_id,
        base_price=payload.base_price,
        notes=payload.notes,
        status="draft"
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    await record_audit(db, int(current_user.id), "POST /orders", payload.model_dump())
    
    return OrderOut(
        id=order.id,
        lead_id=order.lead_id,
        status=order.status,
        base_price=order.base_price,
        final_price=order.final_price,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@router.get("/", response_model=List[OrderOut])
async def list_orders(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    q = select(Order).options(selectinload(Order.lead))
    
    if current_user.role == "agent":
        q = q.join(Lead).where(Lead.created_by == int(current_user.id))
    
    if status:
        q = q.where(Order.status == status)
    
    q = q.limit(limit).offset(offset)
    res = await db.execute(q)
    rows = res.scalars().all()
    
    return [
        OrderOut(
            id=r.id,
            lead_id=r.lead_id,
            status=r.status,
            base_price=r.base_price,
            final_price=r.final_price,
            notes=r.notes,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ) for r in rows
    ]

@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    res = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.lead))
    )
    order = res.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if current_user.role == "agent" and order.lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return OrderOut(
        id=order.id,
        lead_id=order.lead_id,
        status=order.status,
        base_price=order.base_price,
        final_price=order.final_price,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@router.put("/{order_id}", response_model=OrderOut)
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.lead))
    )
    order = res.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if current_user.role == "agent" and order.lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    valid_statuses = {"draft", "quoted", "booked", "delivered"}
    if payload.status and payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")
    
    old_status = order.status
    
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(order, field, value)
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    await record_audit(db, int(current_user.id), f"PUT /orders/{order_id}", payload.model_dump())
    
    if old_status != order.status and order.status in ["quoted", "booked"]:
        await send_webhook({
            "order_id": order.id,
            "final_price": order.final_price or order.base_price,
            "status": order.status
        })
    
    return OrderOut(
        id=order.id,
        lead_id=order.lead_id,
        status=order.status,
        base_price=order.base_price,
        final_price=order.final_price,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.lead))
    )
    order = res.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if current_user.role == "agent" and order.lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    await db.delete(order)
    await db.commit()
    await record_audit(db, int(current_user.id), f"DELETE /orders/{order_id}", {})
    
    return {"deleted": True}

@router.post("/{order_id}/reprice")
async def reprice(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Order).where(Order.id == order_id))
    order = res.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    reprice_order.delay(order_id)
    await record_audit(db, int(current_user.id), f"POST /orders/{order_id}/reprice", {"order_id": order_id})
    
    return {"status": "queued"}
