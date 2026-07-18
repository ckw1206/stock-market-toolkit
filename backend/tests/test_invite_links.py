"""Invite responses expose a full registration link."""

from app.schemas import InviteCodeResponse


def test_invite_code_response_has_invite_link_field():
    assert "invite_link" in InviteCodeResponse.model_fields


def test_build_invite_link_uses_frontend_url(monkeypatch):
    from app.config import get_settings
    from app.routes.admin import build_invite_link

    monkeypatch.setattr(get_settings(), "FRONTEND_URL", "https://stock.example.com/")
    assert build_invite_link("abc123") == "https://stock.example.com/register?token=abc123"


def test_build_invite_link_relative_when_unset(monkeypatch):
    from app.config import get_settings
    from app.routes.admin import build_invite_link

    monkeypatch.setattr(get_settings(), "FRONTEND_URL", "")
    assert build_invite_link("abc123") == "/register?token=abc123"
