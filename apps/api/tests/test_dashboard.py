"""HTTP integration tests for dashboard endpoints."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/v1"
SIGNUP_URL = f"{BASE}/auth/signup"
LOGIN_URL = f"{BASE}/auth/login"
PROJECTS_URL = f"{BASE}/projects"
DASHBOARD_URL = f"{BASE}/dashboard"


@asynccontextmanager
async def _client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def _make_user(
    client: AsyncClient, prefix: str = "u"
) -> tuple[dict[str, object], str]:
    email = f"{prefix}+{uuid.uuid4().hex[:8]}@dash.example"
    r = await client.post(
        SIGNUP_URL,
        json={"email": email, "name": "Dash User", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    return r.json(), email


async def _login(client: AsyncClient, email: str) -> str:
    r = await client.post(LOGIN_URL, json={"email": email, "password": "Password123"})
    assert r.status_code == 200
    token: str = r.json()["access_token"]
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client: AsyncClient, token: str) -> dict[str, object]:
    r = await client.post(
        PROJECTS_URL,
        json={"name": f"Proj-{uuid.uuid4().hex[:6]}"},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    result: dict[str, object] = r.json()
    return result


async def _create_task(
    client: AsyncClient, token: str, project_id: str, **overrides: object
) -> dict[str, object]:
    payload: dict[str, object] = {"title": f"Task-{uuid.uuid4().hex[:6]}", **overrides}
    r = await client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        json=payload,
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    result: dict[str, object] = r.json()
    return result


# ── /dashboard/stats ──────────────────────────────────────────────────────────


async def test_stats_requires_auth() -> None:
    async with _client() as c:
        r = await c.get(f"{DASHBOARD_URL}/stats")
    assert r.status_code == 401


async def test_stats_empty_user_returns_zeros() -> None:
    async with _client() as c:
        _, email = await _make_user(c, "stats_zero")
        token = await _login(c, email)
        r = await c.get(f"{DASHBOARD_URL}/stats", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["open"] == 0
    assert data["overdue"] == 0
    assert data["due_this_week"] == 0


async def test_stats_counts_open_tasks() -> None:
    async with _client() as c:
        _, email = await _make_user(c, "stats_count")
        token = await _login(c, email)
        proj = await _create_project(c, token)
        pid = str(proj["id"])
        await _create_task(c, token, pid)
        await _create_task(c, token, pid)
        r = await c.get(f"{DASHBOARD_URL}/stats", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["open"] == 2


# ── /dashboard/my-tasks ───────────────────────────────────────────────────────


async def test_my_tasks_requires_auth() -> None:
    async with _client() as c:
        r = await c.get(f"{DASHBOARD_URL}/my-tasks")
    assert r.status_code == 401


async def test_my_tasks_empty_for_new_user() -> None:
    async with _client() as c:
        _, email = await _make_user(c, "mytasks_http_empty")
        token = await _login(c, email)
        r = await c.get(f"{DASHBOARD_URL}/my-tasks", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_my_tasks_returns_only_assigned_to_me() -> None:
    async with _client() as c:
        _, email_owner = await _make_user(c, "mytasks_owner")
        token_owner = await _login(c, email_owner)
        user_data, email_me = await _make_user(c, "mytasks_me")
        token_me = await _login(c, email_me)

        proj = await _create_project(c, token_owner)
        pid = str(proj["id"])
        # Invite me as member (endpoint takes email, not user_id)
        r_invite = await c.post(
            f"{PROJECTS_URL}/{pid}/members",
            json={"email": email_me, "role": "member"},
            headers=_auth(token_owner),
        )
        assert r_invite.status_code == 201, r_invite.text
        # Assign one task to me
        await _create_task(c, token_owner, pid, assignee_id=user_data["user"]["id"])
        # Unassigned task
        await _create_task(c, token_owner, pid)

        r = await c.get(f"{DASHBOARD_URL}/my-tasks", headers=_auth(token_me))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["project"]["id"] == pid


async def test_my_tasks_limit_param() -> None:
    async with _client() as c:
        _, email = await _make_user(c, "mytasks_limit")
        token = await _login(c, email)
        proj = await _create_project(c, token)
        pid = str(proj["id"])
        # Get own user id
        me = (await c.get(f"{BASE}/auth/me", headers=_auth(token))).json()
        for _ in range(5):
            await _create_task(c, token, pid, assignee_id=me["id"])

        r = await c.get(f"{DASHBOARD_URL}/my-tasks?limit=3", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5


# ── /dashboard/recent-activity ────────────────────────────────────────────────


async def test_recent_activity_requires_auth() -> None:
    async with _client() as c:
        r = await c.get(f"{DASHBOARD_URL}/recent-activity")
    assert r.status_code == 401


async def test_recent_activity_empty_for_new_user() -> None:
    async with _client() as c:
        _, email = await _make_user(c, "activity_http_empty")
        token = await _login(c, email)
        r = await c.get(f"{DASHBOARD_URL}/recent-activity", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_recent_activity_shows_events_for_my_projects() -> None:
    async with _client() as c:
        _, email = await _make_user(c, "activity_http_events")
        token = await _login(c, email)
        proj = await _create_project(c, token)
        pid = str(proj["id"])
        await _create_task(c, token, pid)

        r = await c.get(f"{DASHBOARD_URL}/recent-activity", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["items"][0]["project_id"] == pid


async def test_recent_activity_does_not_show_others_projects() -> None:
    async with _client() as c:
        _, email_owner = await _make_user(c, "activity_http_scope_owner")
        token_owner = await _login(c, email_owner)
        _, email_other = await _make_user(c, "activity_http_scope_other")
        token_other = await _login(c, email_other)

        proj = await _create_project(c, token_owner)
        pid = str(proj["id"])
        await _create_task(c, token_owner, pid)

        r = await c.get(f"{DASHBOARD_URL}/recent-activity", headers=_auth(token_other))
    assert r.status_code == 200
    assert r.json()["total"] == 0
