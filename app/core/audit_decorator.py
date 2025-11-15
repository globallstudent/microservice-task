import hashlib
import json
import logging
from functools import wraps
from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import Audit

logger = logging.getLogger(__name__)


def audit_log(endpoint_name: str) -> Callable:

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            db: AsyncSession = kwargs.get("db")
            current_user = kwargs.get("current_user")
            
            if not db or not current_user:
                return result
            
            try:
                payload = None
                for key in ["payload", "order", "lead", "data", "body"]:
                    if key in kwargs:
                        payload = kwargs[key]
                        break
                
                if payload is None and args:
                    payload = args[0] if args else {}
                
                if hasattr(payload, "model_dump"):
                    payload_dict = payload.model_dump(exclude_unset=True)
                elif isinstance(payload, dict):
                    payload_dict = payload
                else:
                    payload_dict = {}
                
                payload_str = json.dumps(payload_dict, sort_keys=True, default=str)
                payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
                
                audit_record = Audit(
                    user_id=int(current_user.id),
                    endpoint=endpoint_name,
                    payload_hash=payload_hash,
                )
                db.add(audit_record)
                await db.flush()
                
            except Exception as e:
                logger.error(f"Audit logging failed for {endpoint_name}: {e}")
            
            return result
        
        return wrapper
    return decorator
