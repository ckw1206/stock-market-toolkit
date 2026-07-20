from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, index=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    used_by = Column(String, ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    email = Column(String, nullable=True)
    token = Column(String, nullable=True, unique=True, index=True)

    creator = relationship("User", foreign_keys=[created_by])
    redeemer = relationship("User", foreign_keys=[used_by])


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String, nullable=False, index=True)  # "nightly_ingest"
    status = Column(String, nullable=False)  # "running" | "completed" | "failed"
    symbols_processed = Column(Integer, default=0)
    total_symbols = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    error_details = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class SmtpSettings(Base):
    __tablename__ = "smtp_settings"

    id = Column(Integer, primary_key=True, default=1)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False, default=587)
    use_tls = Column(Boolean, default=True)
    username = Column(String, nullable=True)
    password_encrypted = Column(Text, nullable=True)
    from_address = Column(String, nullable=False)
    reply_to = Column(String, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False, index=True)
    target = Column(String, nullable=True)
    meta = Column(Text, nullable=True)
    ip = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actor = relationship("User", foreign_keys=[actor_id])


class AccountRequest(Base):
    __tablename__ = "account_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, index=True, nullable=False)
    note = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    invite_id = Column(Integer, ForeignKey("invite_codes.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invite = relationship("InviteCode", foreign_keys=[invite_id])
