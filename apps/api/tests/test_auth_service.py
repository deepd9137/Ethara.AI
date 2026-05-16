"""
Direct service-layer tests for auth_service.
These run in the same coroutine context as the test so coverage.py
can properly track async code (ASGITransport creates new tasks that
don't inherit sys.settrace).
"""

import contextlib
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.middleware.exceptions import BusinessError
from app.repositories import refresh_token_repo, user_repo
from app.services import auth_service


def _email(prefix: str = "svc") -> str:
    return f"{prefix}+{uuid.uuid4().hex[:8]}@test.com"


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


# ── signup ────────────────────────────────────────────────────────────────────


async def test_svc_signup_creates_user(db: AsyncSession) -> None:
    em = _email("signup")
    user, access, refresh = await auth_service.signup(
        db, email=em, name="Test User", password="Password123"
    )
    assert user.email == em
    assert access
    assert refresh


async def test_svc_signup_duplicate_raises(db: AsyncSession) -> None:
    em = _email("dup")
    await auth_service.signup(db, email=em, name="T", password="Password123")
    with pytest.raises(BusinessError) as exc:
        await auth_service.signup(db, email=em, name="T", password="Password123")
    assert exc.value.code == "EMAIL_TAKEN"
    assert exc.value.status_code == 409


# ── login ─────────────────────────────────────────────────────────────────────


async def test_svc_login_success(db: AsyncSession) -> None:
    em = _email("loginok")
    await auth_service.signup(db, email=em, name="T", password="Password123")
    user, access, refresh = await auth_service.login(
        db, email=em, password="Password123"
    )
    assert user.email == em
    assert access
    assert refresh


async def test_svc_login_wrong_password(db: AsyncSession) -> None:
    em = _email("badpw")
    await auth_service.signup(db, email=em, name="T", password="Password123")
    with pytest.raises(BusinessError) as exc:
        await auth_service.login(db, email=em, password="wrong")
    assert exc.value.code == "INVALID_CREDENTIALS"


async def test_svc_login_unknown_email(db: AsyncSession) -> None:
    with pytest.raises(BusinessError) as exc:
        await auth_service.login(db, email=_email("ghost"), password="any")
    assert exc.value.code == "INVALID_CREDENTIALS"


async def test_svc_login_lockout(db: AsyncSession) -> None:
    em = _email("lock")
    await auth_service.signup(db, email=em, name="T", password="Password123")
    for _ in range(10):
        with contextlib.suppress(BusinessError):
            await auth_service.login(db, email=em, password="wrong")
    with pytest.raises(BusinessError) as exc:
        await auth_service.login(db, email=em, password="wrong")
    assert exc.value.code == "ACCOUNT_LOCKED"
    assert exc.value.status_code == 423


async def test_svc_login_resets_failed_count_on_success(db: AsyncSession) -> None:
    em = _email("reset")
    await auth_service.signup(db, email=em, name="T", password="Password123")
    for _ in range(3):
        with contextlib.suppress(BusinessError):
            await auth_service.login(db, email=em, password="wrong")
    await auth_service.login(db, email=em, password="Password123")
    user = await user_repo.get_by_email(db, em)
    assert user is not None
    assert user.failed_login_count == 0


# ── rotate_refresh ────────────────────────────────────────────────────────────


async def test_svc_rotate_refresh_issues_new_tokens(db: AsyncSession) -> None:
    em = _email("rot")
    _, _, refresh = await auth_service.signup(db, email=em, name="T", password="P123!")
    new_access, new_refresh = await auth_service.rotate_refresh(db, refresh)
    assert new_access
    assert new_refresh != refresh


async def test_svc_rotate_refresh_expired_raises(db: AsyncSession) -> None:
    em = _email("exp")
    user, _, _ = await auth_service.signup(db, email=em, name="T", password="P123!")
    family_id = uuid.uuid4()
    raw = await refresh_token_repo.issue(db, user_id=user.id, family_id=family_id)
    await db.commit()
    record = await refresh_token_repo.get_by_hash(db, raw)
    assert record is not None
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()
    with pytest.raises(BusinessError) as exc:
        await auth_service.rotate_refresh(db, raw)
    assert exc.value.code == "REFRESH_EXPIRED"


async def test_svc_rotate_refresh_reuse_revokes_family(db: AsyncSession) -> None:
    em = _email("reuse")
    _, _, refresh = await auth_service.signup(db, email=em, name="T", password="P123!")
    _, new_refresh = await auth_service.rotate_refresh(db, refresh)
    # Replay the original token — should revoke the family
    with pytest.raises(BusinessError) as exc:
        await auth_service.rotate_refresh(db, refresh)
    assert exc.value.code == "REFRESH_REUSED"
    # New token should also be revoked
    with pytest.raises(BusinessError):
        await auth_service.rotate_refresh(db, new_refresh)


async def test_svc_rotate_refresh_invalid_token_raises(db: AsyncSession) -> None:
    with pytest.raises(BusinessError) as exc:
        await auth_service.rotate_refresh(db, "not-a-valid-token")
    assert exc.value.code == "REFRESH_EXPIRED"


# ── logout ────────────────────────────────────────────────────────────────────


async def test_svc_logout_revokes_family(db: AsyncSession) -> None:
    em = _email("logout")
    _, _, refresh = await auth_service.signup(db, email=em, name="T", password="P123!")
    await auth_service.logout(db, refresh)
    with pytest.raises(BusinessError):
        await auth_service.rotate_refresh(db, refresh)


async def test_svc_logout_unknown_token_is_noop(db: AsyncSession) -> None:
    await auth_service.logout(db, "nonexistent-token")


# ── change_password ───────────────────────────────────────────────────────────


async def test_svc_change_password_success(db: AsyncSession) -> None:
    em = _email("chpw")
    user, _, __ = await auth_service.signup(db, email=em, name="T", password="OldPass1")
    await auth_service.change_password(
        db, user=user, current_password="OldPass1", new_password="NewPass2"
    )
    _, new_access, _ = await auth_service.login(db, email=em, password="NewPass2")
    assert new_access


async def test_svc_change_password_wrong_current_raises(db: AsyncSession) -> None:
    em = _email("badchpw")
    user, _, _ = await auth_service.signup(db, email=em, name="T", password="Correct1")
    with pytest.raises(BusinessError) as exc:
        await auth_service.change_password(
            db, user=user, current_password="Wrong", new_password="NewPass2"
        )
    assert exc.value.code == "BAD_CURRENT"
