from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select, func
from datetime import datetime, timezone
import uuid
import secrets
from app.models import User, InviteCode
from app.database import get_db
from app.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_admin,  # noqa: F401 — used via Depends() in route handlers
)
from app.services.audit import write_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    # Check existing email
    existing = await db.execute(
        select(User).where(
            (User.email == data.email) | (User.username == data.username.lower())
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Email or username already registered"
        )

    if not data.invite_token:
        raise HTTPException(status_code=400, detail="Invitation required")

    result = await db.execute(
        select(InviteCode).where(InviteCode.token == data.invite_token)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invitation token")
    if not invite.is_active:
        raise HTTPException(status_code=400, detail="Invitation has been revoked")
    expires = invite.expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires and expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation token has expired")
    if invite.used_by is not None:
        raise HTTPException(status_code=400, detail="Invitation token has already been used")

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        username=data.username.lower(),
        hashed_password=hash_password(data.password),
        created_at=func.now(),
    )
    db.add(user)
    await db.flush()

    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)
    await write_audit(
        db,
        actor_id=user.id,
        action="invite.redeemed",
        target=invite.code,
        meta={"token": data.invite_token},
        request=request,
    )

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    user = await db.execute(
        select(User).where(
            (User.email == data.email_or_username)
            | (User.username == data.email_or_username.lower())
        )
    )
    user = user.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        await write_audit(
            db,
            actor_id=None,
            action="login.failed",
            target=data.email_or_username,
            request=request,
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        await write_audit(
            db,
            actor_id=None,
            action="login.failed",
            target=user.email,
            meta={"reason": "account_disabled"},
            request=request,
        )
        raise HTTPException(status_code=403, detail="Account disabled")

    user.last_login_at = func.now()
    await db.commit()

    access = create_access_token({"sub": user.id})
    refresh = create_refresh_token({"sub": user.id})

    await write_audit(
        db,
        actor_id=user.id,
        action="login.success",
        target=user.email,
        request=request,
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    user = await db.get(User, user_id)

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access = create_access_token({"sub": user.id})
    new_refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=200)
async def logout(current_user: User = Depends(get_current_user)):
    # In a production app with refresh token rotation, you would blacklist the token here
    return {"message": "Logged out successfully"}


@router.get("/users/count")
async def get_users_count(db: AsyncSession = Depends(get_db)):
    """Return the total number of users. Used to determine if bootstrap is needed."""
    result = await db.execute(select(func.count()).select_from(User))
    count = result.scalar_one()
    return {"count": count}


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: Optional[str] = None  # If omitted, a random password is generated


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users. Admin only."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {"users": users}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a user's email, admin status, or active status. Admin only."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}
    if data.email is not None:
        existing = await db.execute(
            select(User).where(User.email == data.email, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = data.email
        changes["email"] = data.email
    if data.is_admin is not None:
        user.is_admin = data.is_admin
        changes["is_admin"] = data.is_admin
        await write_audit(
            db,
            actor_id=current_user.id,
            action="user.role_changed",
            target=user.id,
            meta={"is_admin": data.is_admin, "target_user": user.email},
            request=request,
        )
    if data.is_active is not None:
        user.is_active = data.is_active
        changes["is_active"] = data.is_active

    await db.commit()
    await db.refresh(user)
    if changes and "is_admin" not in changes:
        await write_audit(
            db,
            actor_id=current_user.id,
            action="user.updated",
            target=user.id,
            meta=changes,
            request=request,
        )
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a user. Admin only."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return None


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Reset a user's password. Admin only. Returns the new password in plain text."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    generated_password = data.new_password or secrets.token_urlsafe(12)
    user.hashed_password = hash_password(generated_password)
    await db.commit()

    await write_audit(
        db,
        actor_id=current_user.id,
        action="user.password_reset",
        target=user.id,
        meta={"target_user": user.email},
        request=request,
    )
    return {"password": generated_password}


@router.post("/users/{user_id}/change-password")
async def change_user_password(
    user_id: str,
    data: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a user's password. User themselves (with current password) or admin only."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_admin = getattr(current_user, "is_admin", False)
    is_self = current_user.id == user_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not is_admin:
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = hash_password(data.new_password)
    await db.commit()

    await write_audit(
        db,
        actor_id=current_user.id,
        action="user.password_changed",
        target=user.id,
        meta={"target_user": user.email},
        request=request,
    )
    return {"message": "Password changed successfully"}


@router.post("/bootstrap", status_code=201)
async def bootstrap(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Create the first admin user. Only works when no users exist."""
    result = await db.execute(select(func.count()).select_from(User))
    count = result.scalar_one()
    if count > 0:
        raise HTTPException(
            status_code=403, detail="Bootstrap not allowed: users already exist"
        )

    existing = await db.execute(
        select(User).where(
            (User.email == data.email) | (User.username == data.username.lower())
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Email or username already registered"
        )

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        username=data.username.lower(),
        hashed_password=hash_password(data.password),
        is_admin=True,
        created_at=func.now(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
