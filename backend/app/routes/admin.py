from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import secrets
import json
from pathlib import Path
from typing import Optional
from app.models import User, InviteCode, SmtpSettings, AccountRequest
from app.database import get_db
from app.schemas import (
    InviteCodeCreate,
    InviteCodeResponse,
    InviteCodeListResponse,
    InviteSendRequest,
    InviteSendResponse,
    InviteRevokeRequest,
    SmtpSettingsResponse,
    SmtpSettingsUpdate,
    SmtpTestRequest,
    SmtpTestResponse,
    AuditLogListResponse,
    AccountRequestResponse,
    AccountRequestListResponse,
    AccountRequestApproveResponse,
)
from app.auth import require_admin
from app.utils.crypto import encrypt
from app.services.mailer import send_test_email, send_email
from app.services.audit import write_audit, get_audit_logs
from app.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


def generate_code() -> str:
    """Generate a secure random invite code."""
    return secrets.token_urlsafe(16)


def build_invite_link(token: str) -> str:
    """Full registration link for an invite token; relative if FRONTEND_URL unset."""
    settings = get_settings()
    if not settings.FRONTEND_URL:
        return f"/register?token={token}"
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/register?token={token}"


@router.post("/invite-codes", response_model=InviteCodeResponse, status_code=201)
async def create_invite_code(
    data: InviteCodeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Generate a new invitation code. Requires authentication."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    invite = InviteCode(
        code=generate_code(),
        token=secrets.token_urlsafe(32),
        created_by=current_user.id,
        expires_at=expires_at,
        is_active=True,
        email=data.email,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    await write_audit(
        db,
        actor_id=current_user.id,
        action="invite.created",
        target=invite.code,
        meta={"expires_in_days": data.expires_in_days, "has_email": bool(data.email)},
        request=request,
    )
    resp = InviteCodeResponse.model_validate(invite)
    resp.invite_link = build_invite_link(invite.token)
    return resp


@router.get("/invite-codes", response_model=InviteCodeListResponse)
async def list_invite_codes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all invitation codes. Requires authentication."""
    result = await db.execute(select(InviteCode).order_by(InviteCode.created_at.desc()))
    codes = result.scalars().all()

    items = []
    for c in codes:
        item = InviteCodeResponse.model_validate(c)
        if c.token:
            item.invite_link = build_invite_link(c.token)
        items.append(item)

    return InviteCodeListResponse(codes=items, total=len(codes))


@router.delete("/invite-codes/{code_id}", status_code=204)
async def deactivate_invite_code(
    code_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deactivate an invitation code. Requires authentication."""
    invite = await db.get(InviteCode, code_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation code not found")

    invite.is_active = False
    await db.commit()
    await write_audit(
        db,
        actor_id=current_user.id,
        action="invite.revoked",
        target=invite.code,
        meta={"invite_id": code_id},
        request=request,
    )
    return None


@router.delete("/invite-codes/{code_id}/permanent", status_code=204)
async def permanent_delete_invite_code(
    code_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Hard-delete an invite code. Only deletable when the link is dead
    (deactivated or expired) and was never redeemed."""
    invite = await db.get(InviteCode, code_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation code not found")

    now = datetime.now(timezone.utc)
    expires_at = (
        invite.expires_at.replace(tzinfo=timezone.utc)
        if invite.expires_at.tzinfo is None
        else invite.expires_at
    )
    is_expired = expires_at < now
    is_live = invite.is_active and not is_expired
    if invite.used_by is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a redeemed invite code that has been used.",
        )
    if is_live:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an active, unexpired invite code. Deactivate it first.",
        )

    # Null out invite_id on referencing account requests
    result = await db.execute(
        select(AccountRequest).where(AccountRequest.invite_id == code_id)
    )
    for ar in result.scalars():
        ar.invite_id = None

    code_value = invite.code
    await db.delete(invite)
    await db.commit()

    await write_audit(
        db,
        actor_id=current_user.id,
        action="invite.deleted",
        target=code_value,
        meta={"invite_id": code_id},
        request=request,
    )
    return None


@router.post("/invite-send", response_model=InviteSendResponse, status_code=201)
async def send_invite(
    data: InviteSendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create an email-based invitation and send it. Admin only.
    If SMTP is not configured, returns the invite link in the response."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    token = secrets.token_urlsafe(32)
    code = generate_code()

    invite = InviteCode(
        code=code,
        token=token,
        created_by=current_user.id,
        expires_at=expires_at,
        is_active=True,
        email=data.email,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    invite_link = build_invite_link(token)

    await write_audit(
        db,
        actor_id=current_user.id,
        action="invite.sent",
        target=data.email,
        meta={"invite_code": code, "token": token},
        request=request,
    )

    return InviteSendResponse(
        message="Invitation created. SMTP not configured — invite link returned in response.",
        invite_code=code,
        token=token,
        invite_link=invite_link,
    )


@router.post("/invite-revoke")
async def revoke_invite(
    data: InviteRevokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Revoke an invitation by token. Admin only."""
    result = await db.execute(
        select(InviteCode).where(InviteCode.token == data.token)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invite.is_active = False
    await db.commit()

    await write_audit(
        db,
        actor_id=current_user.id,
        action="invite.revoked",
        target=invite.code,
        meta={"token": data.token},
        request=request,
    )
    return {"message": "Invitation revoked"}


@router.get("/account-requests", response_model=AccountRequestListResponse)
async def list_account_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List account requests, newest first. Admin only."""
    result = await db.execute(
        select(AccountRequest).order_by(AccountRequest.created_at.desc())
    )
    requests = result.scalars().all()
    return AccountRequestListResponse(
        requests=[AccountRequestResponse.model_validate(r) for r in requests],
        total=len(requests),
    )


@router.post("/account-requests/{request_id}/approve", response_model=AccountRequestApproveResponse)
async def approve_account_request(
    request_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Approve a pending request: create an invite for its email and return the link.
    Sends the link by email when SMTP is configured; the link is always returned."""
    req = await db.get(AccountRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")

    token = secrets.token_urlsafe(32)
    invite = InviteCode(
        code=generate_code(),
        token=token,
        created_by=current_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_active=True,
        email=req.email,
    )
    db.add(invite)
    await db.flush()

    req.status = "approved"
    req.invite_id = invite.id
    await db.commit()

    invite_link = build_invite_link(token)

    email_sent = False
    smtp = await db.get(SmtpSettings, 1)
    if smtp and smtp.host and smtp.from_address:
        email_sent = await send_email(
            smtp,
            to=req.email,
            subject="Your Stock Market Toolkit invitation",
            html_body=(
                "<p>Your account request has been approved.</p>"
                f'<p><a href="{invite_link}">Click here to create your account</a> '
                "(link expires in 7 days).</p>"
            ),
        )

    await write_audit(
        db,
        actor_id=current_user.id,
        action="account_request.approved",
        target=req.email,
        meta={"request_id": request_id, "invite_id": invite.id, "email_sent": email_sent},
        request=request,
    )

    return AccountRequestApproveResponse(
        message="Request approved",
        invite_link=invite_link,
        token=token,
        email_sent=email_sent,
    )


@router.post("/account-requests/{request_id}/deny")
async def deny_account_request(
    request_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deny a pending account request. Admin only."""
    req = await db.get(AccountRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")

    req.status = "denied"
    await write_audit(
        db,
        actor_id=current_user.id,
        action="account_request.denied",
        target=req.email,
        meta={"request_id": request_id},
        request=request,
    )
    return {"message": "Request denied"}


@router.get("/smtp", response_model=SmtpSettingsResponse)
async def get_smtp_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.get(SmtpSettings, 1)
    if not result:
        raise HTTPException(status_code=404, detail="SMTP settings not configured")
    return SmtpSettingsResponse(
        host=result.host,
        port=result.port,
        use_tls=result.use_tls,
        username=result.username,
        password_set=bool(result.password_encrypted),
        from_address=result.from_address,
        reply_to=result.reply_to,
        updated_at=result.updated_at,
    )


@router.put("/smtp", response_model=SmtpSettingsResponse)
async def upsert_smtp_settings(
    data: SmtpSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    settings = await db.get(SmtpSettings, 1)
    if settings is None:
        settings = SmtpSettings(id=1)
        db.add(settings)

    if data.host is not None:
        settings.host = data.host
    if data.port is not None:
        settings.port = data.port
    if data.use_tls is not None:
        settings.use_tls = data.use_tls
    if data.username is not None:
        settings.username = data.username
    if data.password is not None:
        settings.password_encrypted = encrypt(data.password)
    if data.from_address is not None:
        settings.from_address = data.from_address
    if data.reply_to is not None:
        settings.reply_to = data.reply_to

    await db.commit()
    await db.refresh(settings)

    return SmtpSettingsResponse(
        host=settings.host,
        port=settings.port,
        use_tls=settings.use_tls,
        username=settings.username,
        password_set=bool(settings.password_encrypted),
        from_address=settings.from_address,
        reply_to=settings.reply_to,
        updated_at=settings.updated_at,
    )


@router.post("/smtp/test", response_model=SmtpTestResponse)
async def test_smtp_settings(
    data: SmtpTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    settings = await db.get(SmtpSettings, 1)
    if not settings:
        raise HTTPException(status_code=404, detail="SMTP settings not configured")
    if not settings.host or not settings.from_address:
        raise HTTPException(status_code=400, detail="SMTP host and from_address must be configured")

    success, message = await send_test_email(settings, data.to_email)
    return SmtpTestResponse(success=success, message=message)


@router.get("/logs")
async def get_logs(
    level: Optional[str] = Query(
        None, description="Filter by log level (e.g. INFO, ERROR)"
    ),
    since: Optional[str] = Query(
        None, description="ISO datetime filter (logs after this time)"
    ),
    limit: int = Query(100, ge=1, le=10000, description="Max number of log entries"),
    search: Optional[str] = Query(None, description="Text search across log entries"),
    current_user: User = Depends(require_admin),
):
    log_file = Path(__file__).resolve().parent.parent.parent / "logs" / "app.json"

    if not log_file.exists():
        return {"logs": [], "total": 0}

    entries: list[dict] = []
    try:
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return {"logs": [], "total": 0}

    if level:
        level_upper = level.upper()
        entries = [e for e in entries if e.get("level") == level_upper]

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            entries = [
                e
                for e in entries
                if e.get("timestamp")
                and datetime.fromisoformat(e["timestamp"]) >= since_dt
            ]
        except ValueError:
            pass

    if search:
        search_lower = search.lower()
        entries = [
            e for e in entries if search_lower in json.dumps(e, default=str).lower()
        ]

    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    total = len(entries)
    entries = entries[:limit]

    return {"logs": entries, "total": total}


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor: Optional[str] = Query(None, description="Filter by actor user ID"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    date_from: Optional[str] = Query(
        None, description="ISO date filter (inclusive, e.g. 2026-01-01)"
    ),
    date_to: Optional[str] = Query(
        None, description="ISO date filter (inclusive, e.g. 2026-06-30)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List audit log entries with pagination and filters. Admin only."""
    logs, total = await get_audit_logs(
        db,
        actor=actor,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )
    return AuditLogListResponse(logs=logs, total=total)


@router.get("/access-logs")
async def get_access_logs(
    since: Optional[str] = Query(
        None, description="ISO datetime filter (logs after this time)"
    ),
    limit: int = Query(100, ge=1, le=10000, description="Max number of log entries"),
    search: Optional[str] = Query(None, description="Text search across log entries"),
    status: Optional[int] = Query(
        None, description="Filter by HTTP status code"
    ),
    current_user: User = Depends(require_admin),
):
    log_file = Path(__file__).resolve().parent.parent.parent / "logs" / "app.json"

    if not log_file.exists():
        return {"logs": [], "total": 0}

    entries: list[dict] = []
    try:
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    if parsed.get("type") == "access":
                        entries.append(parsed)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return {"logs": [], "total": 0}

    if status is not None:
        entries = [e for e in entries if e.get("status") == status]

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            entries = [
                e
                for e in entries
                if e.get("timestamp")
                and datetime.fromisoformat(e["timestamp"]) >= since_dt
            ]
        except ValueError:
            pass

    if search:
        search_lower = search.lower()
        entries = [
            e for e in entries if search_lower in json.dumps(e, default=str).lower()
        ]

    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    total = len(entries)
    entries = entries[:limit]

    return {"logs": entries, "total": total}
