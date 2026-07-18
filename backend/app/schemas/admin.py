from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional


class InviteCodeCreate(BaseModel):
    expires_in_days: int = Field(default=7, ge=1, le=365)
    email: Optional[str] = None


class InviteCodeResponse(BaseModel):
    id: int
    code: str
    created_by: str
    used_by: Optional[str] = None
    used_at: Optional[datetime] = None
    expires_at: datetime
    is_active: bool
    created_at: Optional[datetime] = None
    email: Optional[str] = None
    token: Optional[str] = None
    invite_link: Optional[str] = None

    class Config:
        from_attributes = True


class InviteCodeListResponse(BaseModel):
    codes: list[InviteCodeResponse]
    total: int


class InviteSendRequest(BaseModel):
    email: EmailStr


class InviteSendResponse(BaseModel):
    message: str
    invite_code: str
    token: str
    invite_link: Optional[str] = None


class InviteRevokeRequest(BaseModel):
    token: str


class AuditLogResponse(BaseModel):
    id: int
    actor_id: Optional[str] = None
    action: str
    target: Optional[str] = None
    meta: Optional[dict] = None
    ip: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("meta", mode="before")
    @classmethod
    def parse_meta(cls, v):
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int


class SmtpSettingsResponse(BaseModel):
    host: str
    port: int
    use_tls: bool
    username: Optional[str] = None
    password_set: bool
    from_address: str
    reply_to: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SmtpSettingsUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    use_tls: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_address: Optional[str] = None
    reply_to: Optional[str] = None


class SmtpTestRequest(BaseModel):
    to_email: EmailStr


class SmtpTestResponse(BaseModel):
    success: bool
    message: str


class AccountRequestCreate(BaseModel):
    email: EmailStr
    note: Optional[str] = Field(default=None, max_length=1000)


class AccountRequestResponse(BaseModel):
    id: int
    email: str
    note: Optional[str] = None
    status: str
    invite_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AccountRequestListResponse(BaseModel):
    requests: list[AccountRequestResponse]
    total: int


class AccountRequestApproveResponse(BaseModel):
    message: str
    invite_link: str
    token: str
    email_sent: bool
