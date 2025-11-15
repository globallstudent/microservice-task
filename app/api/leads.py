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
from app.core.config import settings
from app.utils.idempotency import get_idempotent, set_idempotent
from app.core.audit_decorator import audit_log
from app.core.rate_limit import check_rate_limit
from app.core.auth_utils import verify_resource_owner, filter_by_user, check_ownership, check_not_found
from app.core.response_builders import build_lead_response, build_lead_response_list

router = APIRouter(prefix="/leads", tags=["leads"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=LeadOut)
@audit_log("create_lead")
async def create_lead(
    payload: LeadCreate,
    idempotency_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
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

    out = build_lead_response(lead)
    if idempotency_key:
        await set_idempotent(idempotency_key, out.model_dump())
    return out


@router.get("/", response_model=List[LeadOut])
async def list_leads(
    origin_zip: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    q = select(Lead).options(selectinload(Lead.creator))
    
    q = filter_by_user(q, Lead, current_user)
    
    if origin_zip:
        q = q.filter(Lead.origin_zip == origin_zip)
    
    q = q.limit(limit).offset(offset)
    res = await db.execute(q)
    leads = res.scalars().all()
    
    return build_lead_response_list(leads)


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    res = await db.execute(
        select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.creator))
    )
    lead = res.scalars().first()
    check_not_found(lead, "Lead", lead_id)
    check_ownership(lead, current_user, "Lead")
    
    return build_lead_response(lead)


@router.put("/{lead_id}", response_model=LeadOut)
@audit_log("update_lead")
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update a lead"""
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalars().first()
    check_not_found(lead, "Lead", lead_id)
    check_ownership(lead, current_user, "Lead")
    
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    
    return build_lead_response(lead)


@router.delete("/{lead_id}")
@audit_log("delete_lead")
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalars().first()
    check_not_found(lead, "Lead", lead_id)
    check_ownership(lead, current_user, "Lead")
    
    await db.delete(lead)
    await db.commit()
    
    return {"deleted": True}


@router.post("/{lead_id}/attachments")
@audit_log("upload_attachment")
async def upload_attachment(
    lead_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    await check_rate_limit(int(current_user.id))
    
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalars().first()
    check_not_found(lead, "Lead", lead_id)
    check_ownership(lead, current_user, "Lead")
    
    if not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only images and PDFs allowed.")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
        )
    
    safe_filename = f"{lead_id}_{secrets.token_hex(8)}_{file.filename}"
    path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    with open(path, "wb") as f:
        f.write(content)
    
    att = Attachment(
        lead_id=lead_id,
        filename=safe_filename,
        content_type=file.content_type,
        size=len(content)
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    
    return {"ok": True, "id": att.id, "filename": safe_filename}
