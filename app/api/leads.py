from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
import os
import secrets
from app.db.session import get_db
from app.models.lead import Lead
from app.models.attachment import Attachment
from app.schemas.lead import LeadCreate, LeadUpdate, LeadOut
from app.core.security import get_current_user
from app.utils.idempotency import get_idempotent, set_idempotent
from app.core.audit import record_audit
from app.core.rate_limit import check_rate_limit

router = APIRouter(prefix="/leads", tags=["leads"])
UPLOAD_DIR = "./data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=LeadOut)
async def create_lead(
    payload: LeadCreate,
    idempotency_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    if idempotency_key:
        prev = await get_idempotent(idempotency_key)
        if prev:
            return prev

    lead = Lead(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        origin_zip=payload.origin_zip,
        dest_zip=payload.dest_zip,
        vehicle_type=payload.vehicle_type,
        operable=payload.operable,
        created_by=int(current_user.id),
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await record_audit(db, int(current_user.id), "POST /leads", payload.model_dump())

    out = LeadOut(
        id=lead.id,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        origin_zip=lead.origin_zip,
        dest_zip=lead.dest_zip,
        vehicle_type=lead.vehicle_type,
        operable=lead.operable,
        created_by=lead.created_by,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )
    if idempotency_key:
        await set_idempotent(idempotency_key, out.model_dump())
    return out

@router.get("/", response_model=List[LeadOut])
async def list_leads(
    origin_zip: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    q = select(Lead).options(selectinload(Lead.creator))
    
    if current_user.role == "agent":
        q = q.where(Lead.created_by == int(current_user.id))
    
    if origin_zip:
        q = q.filter(Lead.origin_zip == origin_zip)
    q = q.limit(limit).offset(offset)
    res = await db.execute(q)
    rows = res.scalars().all()
    return [
        LeadOut(
            id=r.id,
            name=r.name,
            phone=r.phone,
            email=r.email,
            origin_zip=r.origin_zip,
            dest_zip=r.dest_zip,
            vehicle_type=r.vehicle_type,
            operable=r.operable,
            created_by=r.created_by,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ) for r in rows
    ]

@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    res = await db.execute(
        select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.creator))
    )
    lead = res.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if current_user.role == "agent" and lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return LeadOut(
        id=lead.id,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        origin_zip=lead.origin_zip,
        dest_zip=lead.dest_zip,
        vehicle_type=lead.vehicle_type,
        operable=lead.operable,
        created_by=lead.created_by,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )

@router.put("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if current_user.role == "agent" and lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(lead, field, value)
    
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await record_audit(db, int(current_user.id), f"PUT /leads/{lead_id}", payload.model_dump())
    
    return LeadOut(
        id=lead.id,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        origin_zip=lead.origin_zip,
        dest_zip=lead.dest_zip,
        vehicle_type=lead.vehicle_type,
        operable=lead.operable,
        created_by=lead.created_by,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )

@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if current_user.role == "agent" and lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    await db.delete(lead)
    await db.commit()
    await record_audit(db, int(current_user.id), f"DELETE /leads/{lead_id}", {})
    
    return {"deleted": True}

@router.post("/{lead_id}/attachments")
async def upload_attachment(
    lead_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    # Check lead exists and user has access
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if current_user.role == "agent" and lead.created_by != int(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Sanitize filename
    safe_filename = f"{lead_id}_{secrets.token_hex(8)}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(path, "wb") as f:
        f.write(content)
    
    att = Attachment(lead_id=lead_id, filename=safe_filename, content_type=file.content_type, size=len(content))
    db.add(att)
    await db.commit()
    await db.refresh(att)
    await record_audit(db, int(current_user.id), f"POST /leads/{lead_id}/attachments", {"filename": safe_filename})
    
    return {"ok": True, "id": att.id}
