import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "https://test"
SIGNUP_URL = "/v1/auth/signup"
LOGIN_URL = "/v1/auth/login"
REFRESH_URL = "/v1/auth/refresh"
LOGOUT_URL = "/v1/auth/logout"
ME_URL = "/v1/auth/me"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


def _email(prefix: str = "user") -> str:
    """Return a unique email for each test run to avoid DB collisions."""
    return f"{prefix}+{uuid.uuid4().hex[:8]}@test.com"


async def _signup(
    client: AsyncClient, email: str | None = None
) -> tuple[dict, str]:  # type: ignore[type-arg]
    em = email or _email()
    r = await client.post(
        SIGNUP_URL, json={"email": em, "name": "Test", "password": "Password123"}
    )
    assert r.status_code == 201, r.text
    return r.json(), em


# ── signup ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_signup_creates_user_and_returns_tokens() -> None:
    async with _client() as c:
        data, em = await _signup(c)
    assert "access_token" in data
    assert data["user"]["email"] == em


@pytest.mark.asyncio
async def test_signup_sets_refresh_cookie() -> None:
    async with _client() as c:
        r = await c.post(
            SIGNUP_URL,
            json={"email": _email("cookie"), "name": "T", "password": "Password123"},
        )
    assert r.status_code == 201
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_409() -> None:
    em = _email("dup")
    async with _client() as c:
        await _signup(c, em)
        r = await c.post(
            SIGNUP_URL,
            json={"email": em, "name": "T", "password": "Password123"},
        )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_TAKEN"


# ── login ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_returns_access_token_and_sets_cookie() -> None:
    em = _email("login")
    async with _client() as c:
        await _signup(c, em)
        r = await c.post(LOGIN_URL, json={"email": em, "password": "Password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401() -> None:
    em = _email("badpw")
    async with _client() as c:
        await _signup(c, em)
        r = await c.post(LOGIN_URL, json={"email": em, "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401() -> None:
    async with _client() as c:
        r = await c.post(
            LOGIN_URL, json={"email": _email("ghost"), "password": "anything"}
        )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_lockout_after_10_failures() -> None:
    em = _email("lock")
    async with _client() as c:
        await _signup(c, em)
        for _ in range(10):
            await c.post(LOGIN_URL, json={"email": em, "password": "wrong"})
        r = await c.post(LOGIN_URL, json={"email": em, "password": "wrong"})
    assert r.status_code == 423
    assert r.json()["error"]["code"] == "ACCOUNT_LOCKED"


# ── /me ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_returns_user_dto() -> None:
    em = _email("me")
    async with _client() as c:
        data, _ = await _signup(c, em)
        r = await c.get(
            ME_URL, headers={"Authorization": f"Bearer {data['access_token']}"}
        )
    assert r.status_code == 200
    assert r.json()["email"] == em


@pytest.mark.asyncio
async def test_me_without_token_returns_401() -> None:
    async with _client() as c:
        r = await c.get(ME_URL)
    assert r.status_code == 401


# ── refresh rotation ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_rotation_issues_new_tokens() -> None:
    async with _client() as c:
        await _signup(c, _email("ref"))
        r = await c.post(REFRESH_URL)
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_family_and_returns_401() -> None:
    async with _client() as c:
        signup_resp = await c.post(
            SIGNUP_URL,
            json={"email": _email("reuse"), "name": "T", "password": "Password123"},
        )
        assert signup_resp.status_code == 201
        original_cookie = signup_resp.cookies["refresh_token"]

        # First use — valid, rotates token
        r1 = await c.post(REFRESH_URL)
        assert r1.status_code == 200

        # Replay original (already-used) token
        c.cookies.set("refresh_token", original_cookie)
        r2 = await c.post(REFRESH_URL)

    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "REFRESH_REUSED"


# ── no PII in logs ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_pii_in_structlog_output(capsys: pytest.CaptureFixture) -> None:  # type: ignore[type-arg]
    secret = "super_secret_password_xyz"
    async with _client() as c:
        await c.post(
            LOGIN_URL,
            json={"email": _email("pii"), "password": secret},
        )
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
