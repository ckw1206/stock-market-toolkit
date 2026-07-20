"""AccountRequest model and schema registry tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base


def test_account_request_model_shape():
    from app.models import AccountRequest

    columns = {c.name: c for c in AccountRequest.__table__.columns}
    assert AccountRequest.__tablename__ == "account_requests"
    assert columns["email"].nullable is False
    assert columns["email"].index is True
    assert columns["note"].nullable is True
    assert columns["status"].nullable is False
    assert columns["invite_id"].nullable is True


def test_account_request_schemas_exist():
    from app.schemas import (
        AccountRequestCreate,
        AccountRequestResponse,
        AccountRequestListResponse,
        AccountRequestApproveResponse,
    )

    assert "email" in AccountRequestCreate.model_fields
    assert "note" in AccountRequestCreate.model_fields
    assert "status" in AccountRequestResponse.model_fields
    assert "invite_id" in AccountRequestResponse.model_fields
    assert "requests" in AccountRequestListResponse.model_fields
    assert "invite_link" in AccountRequestApproveResponse.model_fields
    assert "email_sent" in AccountRequestApproveResponse.model_fields


@pytest.mark.asyncio
async def test_account_request_defaults_to_pending():
    from app.models import AccountRequest

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        req = AccountRequest(email="visitor@test.com", note="hi")
        db.add(req)
        await db.commit()
        await db.refresh(req)
        assert req.status == "pending"
        assert req.invite_id is None
        assert req.created_at is not None
