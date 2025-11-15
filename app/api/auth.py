from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import LoginIn, TokenOut
from app.models.user import User
from app.db.session import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.core.enums import UserRole
from app.core.audit_log import log_audit
from app.core.enums import AuditAction

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
async def register(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.username == payload.username))
    existing_user = res.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = hash_password(payload.password)
    new_user = User(username=payload.username, password_hash=hashed_password, role=UserRole.AGENT)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    await log_audit(db, int(new_user.id), AuditAction.LOGIN, {"username": payload.username})
    
    token = create_access_token(str(new_user.id), new_user.role)
    return {"access_token": token}


@router.post("/login", response_model=TokenOut)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.username == form_data.username))
    user = res.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    await log_audit(db, int(user.id), AuditAction.LOGIN, {"username": form_data.username})
    
    token = create_access_token(str(user.id), user.role)
    return {"access_token": token}
