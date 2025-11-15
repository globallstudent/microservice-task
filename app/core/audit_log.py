"""Enhanced audit logging utilities for database operations"""
import hashlib
import json
import logging
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import Audit
from app.core.enums import AuditAction

logger = logging.getLogger(__name__)


async def log_audit(
    db: AsyncSession,
    user_id: int,
    action: AuditAction,
    payload: Optional[dict] = None
) -> None:

    try:
        if payload is None:
            payload = {}
        
        if hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump(exclude_unset=True)
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            payload_dict = {}
        
        payload_str = json.dumps(payload_dict, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        
        audit_record = Audit(
            user_id=int(user_id),
            endpoint=str(action),
            payload_hash=payload_hash,
        )
        
        db.add(audit_record)
        await db.flush()
        
    except Exception as e:
        logger.error(f"Audit logging failed for action {action}: {e}", exc_info=True)


async def log_create(
    db: AsyncSession,
    user_id: int,
    resource_type: str,
    payload: Optional[dict] = None
) -> None:
    action = AuditAction.CREATE_LEAD if resource_type == "lead" else AuditAction.CREATE_ORDER
    await log_audit(db, user_id, action, payload)


async def log_update(
    db: AsyncSession,
    user_id: int,
    resource_type: str,
    payload: Optional[dict] = None
) -> None:
    action = AuditAction.UPDATE_LEAD if resource_type == "lead" else AuditAction.UPDATE_ORDER
    await log_audit(db, user_id, action, payload)


async def log_delete(
    db: AsyncSession,
    user_id: int,
    resource_type: str,
    resource_id: int
) -> None:
    action = AuditAction.DELETE_LEAD if resource_type == "lead" else AuditAction.DELETE_ORDER
    await log_audit(db, user_id, action, {"id": resource_id})


async def log_login(
    db: AsyncSession,
    user_id: int,
    username: str
) -> None:
    await log_audit(db, user_id, AuditAction.LOGIN, {"username": username})
