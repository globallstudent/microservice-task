from datetime import datetime, timezone
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import Audit

async def record_audit(db: AsyncSession, user_id: int, endpoint: str, payload: dict):
    """Record audit log entry"""
    try:
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        audit = Audit(
            user_id=user_id,
            endpoint=endpoint,
            payload_hash=payload_hash,
        )
        db.add(audit)
        await db.flush()
    except Exception as e:
        import logging
        logging.error(f"Audit logging failed: {e}")
