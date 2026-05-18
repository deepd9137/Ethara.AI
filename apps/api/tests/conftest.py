"""
Test configuration.
- Single session-scoped event loop so asyncpg doesn't get "wrong loop" errors.
- Rate limiter disabled so the 10/5min cap doesn't trigger during the full suite.
- Shared HTTP fixtures (api_client, make_user, auth_headers) to replace per-file
  duplicates of signup/login boilerplate.
"""

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

DEFAULT_PASSWORD = "Password123"


@pytest.fixture(scope="session")
def event_loop_policy() -> object:
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(autouse=True)
def disable_rate_limiting() -> Generator[None, None, None]:
    with patch("app.core.limiter.limiter.enabled", False):
        yield


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the ASGI app — no network."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


MakeUser = Callable[..., Awaitable[tuple[dict[str, Any], str, str]]]


@pytest_asyncio.fixture
async def make_user(api_client: AsyncClient) -> MakeUser:
    """Factory: signs up a unique user and returns (signup_payload, email, access_token).

    Usage:
        data, email, token = await make_user()
        data, email, token = await make_user(prefix="alice")
    """

    async def _make(prefix: str = "u") -> tuple[dict[str, Any], str, str]:
        email = f"{prefix}+{uuid.uuid4().hex[:8]}@ttm.example"
        r = await api_client.post(
            "/v1/auth/signup",
            json={"email": email, "name": "Test User", "password": DEFAULT_PASSWORD},
        )
        assert r.status_code == 201, r.text
        payload: dict[str, Any] = r.json()
        return payload, email, payload["access_token"]

    return _make


@pytest_asyncio.fixture
async def auth_headers(make_user: MakeUser) -> dict[str, str]:
    """Pre-baked Bearer headers for a single fresh user — for tests that just need 'a logged-in user'."""
    _, _, token = await make_user()
    return {"Authorization": f"Bearer {token}"}


def bearer(token: str) -> dict[str, str]:
    """Tiny helper to build Authorization headers from a raw token string."""
    return {"Authorization": f"Bearer {token}"}
