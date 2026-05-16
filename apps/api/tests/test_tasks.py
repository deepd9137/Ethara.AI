"""HTTP integration tests for task management endpoints."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/v1"
SIGNUP_URL = f"{BASE}/auth/signup"
LOGIN_URL = f"{BASE}/auth/login"
PROJECTS_URL = f"{BASE}/projects"


@asynccontextmanager
async def _client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def _make_user(
    client: AsyncClient, prefix: str = "u"
) -> tuple[dict[str, object], str]:
    email = f"{prefix}+{uuid.uuid4().hex[:8]}@task.example"
    r = await client.post(
        SIGNUP_URL,
        json={"email": email, "name": "Test User", "password": "Password123"},
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
    client: AsyncClient,
    token: str,
    project_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": f"Task-{uuid.uuid4().hex[:6]}",
        **overrides,
    }
    r = await client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        json=payload,
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    result: dict[str, object] = r.json()
    return result


# ── create ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_task_returns_201() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "ct")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        assert task["status"] == "todo"
        assert task["priority"] == "medium"
        assert task["assignee_id"] is None


@pytest.mark.asyncio
async def test_create_task_non_member_returns_404() -> None:
    async with _client() as c:
        owner_data, _ = await _make_user(c, "ctnm_owner")
        other_data, _ = await _make_user(c, "ctnm_other")
        owner_token: str = owner_data["access_token"]  # type: ignore[assignment]
        other_token: str = other_data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, owner_token)
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/tasks",
            json={"title": "T"},
            headers=_auth(other_token),
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_task_with_non_member_assignee_returns_422() -> None:
    async with _client() as c:
        owner_data, _ = await _make_user(c, "ctna_owner")
        stranger_data, _ = await _make_user(c, "ctna_stranger")
        owner_token: str = owner_data["access_token"]  # type: ignore[assignment]
        stranger_user: dict[str, object] = stranger_data["user"]  # type: ignore[assignment]
        proj = await _create_project(c, owner_token)
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/tasks",
            json={
                "title": "Task Title",
                "assignee_id": str(stranger_user["id"]),
            },
            headers=_auth(owner_token),
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "ASSIGNEE_NOT_MEMBER"


# ── list ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_tasks_returns_created_task() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "lt")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        await _create_task(c, token, str(proj["id"]))
        r = await c.get(f"{PROJECTS_URL}/{proj['id']}/tasks", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "ltfs")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        await _create_task(c, token, str(proj["id"]))
        r = await c.get(
            f"{PROJECTS_URL}/{proj['id']}/tasks?status=in_progress",
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_tasks_size_capped_at_100() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "ltcap")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        r = await c.get(
            f"{PROJECTS_URL}/{proj['id']}/tasks?size=200",
            headers=_auth(token),
        )
        assert r.status_code == 422  # query param validator rejects > 100


# ── get ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_task_by_id_ok() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "gt")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        r = await c.get(f"{BASE}/tasks/{task['id']}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["id"] == task["id"]


@pytest.mark.asyncio
async def test_get_task_non_member_returns_404() -> None:
    async with _client() as c:
        owner_data, _ = await _make_user(c, "gtnm_owner")
        other_data, _ = await _make_user(c, "gtnm_other")
        owner_token: str = owner_data["access_token"]  # type: ignore[assignment]
        other_token: str = other_data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, owner_token)
        task = await _create_task(c, owner_token, str(proj["id"]))
        r = await c.get(f"{BASE}/tasks/{task['id']}", headers=_auth(other_token))
        assert r.status_code == 404


# ── FSM transitions ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fsm_todo_to_in_progress_ok() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "fsm1")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        r = await c.patch(
            f"{BASE}/tasks/{task['id']}/status",
            json={"status": "in_progress"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_fsm_todo_to_done_rejected() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "fsm2")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        r = await c.patch(
            f"{BASE}/tasks/{task['id']}/status",
            json={"status": "done"},
            headers=_auth(token),
        )
        assert r.status_code == 422
        body = r.json()
        assert body["error"]["code"] == "INVALID_TRANSITION"
        assert "allowed" in body["error"]["details"]


@pytest.mark.asyncio
async def test_fsm_full_path_to_done_then_reopen() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "fsmfull")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        tid = task["id"]

        for status in ("in_progress", "in_review", "done"):
            r = await c.patch(
                f"{BASE}/tasks/{tid}/status",
                json={"status": status},
                headers=_auth(token),
            )
            assert r.status_code == 200, f"Failed at {status}: {r.text}"

        # completed_at should be set
        assert r.json()["completed_at"] is not None

        # reopen: done → in_review clears completed_at
        r = await c.patch(
            f"{BASE}/tasks/{tid}/status",
            json={"status": "in_review"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["completed_at"] is None


@pytest.mark.asyncio
async def test_fsm_in_progress_can_go_back_to_todo() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "fsmbk")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        tid = task["id"]
        await c.patch(
            f"{BASE}/tasks/{tid}/status",
            json={"status": "in_progress"},
            headers=_auth(token),
        )
        r = await c.patch(
            f"{BASE}/tasks/{tid}/status",
            json={"status": "todo"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "todo"


@pytest.mark.asyncio
async def test_fsm_in_review_can_go_back_to_in_progress() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "fsmrev")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        tid = task["id"]
        for status in ("in_progress", "in_review"):
            await c.patch(
                f"{BASE}/tasks/{tid}/status",
                json={"status": status},
                headers=_auth(token),
            )
        r = await c.patch(
            f"{BASE}/tasks/{tid}/status",
            json={"status": "in_progress"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"


# ── update ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_task_title_ok() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "upd")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        r = await c.patch(
            f"{BASE}/tasks/{task['id']}",
            json={"title": "New Title"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_update_task_non_creator_non_admin_returns_403() -> None:
    async with _client() as c:
        owner_data, _owner_email = await _make_user(c, "upd403_owner")
        member_data, member_email = await _make_user(c, "upd403_member")
        owner_token: str = owner_data["access_token"]  # type: ignore[assignment]
        member_token: str = member_data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, owner_token)
        # Invite member as regular member
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": member_email, "role": "member"},
            headers=_auth(owner_token),
        )
        task = await _create_task(c, owner_token, str(proj["id"]))
        r = await c.patch(
            f"{BASE}/tasks/{task['id']}",
            json={"title": "Hijack"},
            headers=_auth(member_token),
        )
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_update_task_if_match_mismatch_returns_412() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "ifm")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        r = await c.patch(
            f"{BASE}/tasks/{task['id']}",
            json={"title": "Stale"},
            headers={**_auth(token), "If-Match": "2000-01-01T00:00:00"},
        )
        assert r.status_code == 412
        assert r.json()["error"]["code"] == "PRECONDITION_FAILED"


# ── delete ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_task_by_creator_ok() -> None:
    async with _client() as c:
        data, _ = await _make_user(c, "del")
        token: str = data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, token)
        task = await _create_task(c, token, str(proj["id"]))
        r = await c.delete(f"{BASE}/tasks/{task['id']}", headers=_auth(token))
        assert r.status_code == 204
        r2 = await c.get(f"{BASE}/tasks/{task['id']}", headers=_auth(token))
        assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_by_non_creator_member_returns_403() -> None:
    async with _client() as c:
        owner_data, _owner_email = await _make_user(c, "del403_owner")
        member_data, member_email = await _make_user(c, "del403_member")
        owner_token: str = owner_data["access_token"]  # type: ignore[assignment]
        member_token: str = member_data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, owner_token)
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": member_email, "role": "member"},
            headers=_auth(owner_token),
        )
        task = await _create_task(c, owner_token, str(proj["id"]))
        r = await c.delete(f"{BASE}/tasks/{task['id']}", headers=_auth(member_token))
        assert r.status_code == 403


# ── member removal nullifies assignments ──────────────────────────────────────


@pytest.mark.asyncio
async def test_member_removal_nullifies_assignments() -> None:
    async with _client() as c:
        owner_data, _owner_email = await _make_user(c, "null_owner")
        member_data, member_email = await _make_user(c, "null_member")
        owner_token: str = owner_data["access_token"]  # type: ignore[assignment]
        proj = await _create_project(c, owner_token)

        # Invite member
        inv_r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": member_email, "role": "member"},
            headers=_auth(owner_token),
        )
        assert inv_r.status_code == 201
        member_user: dict[str, object] = member_data["user"]  # type: ignore[assignment]
        member_user_id = str(member_user["id"])

        # Create task assigned to member
        task = await _create_task(
            c, owner_token, str(proj["id"]), assignee_id=member_user_id
        )
        assert task["assignee_id"] == member_user_id

        # Remove member
        r = await c.delete(
            f"{PROJECTS_URL}/{proj['id']}/members/{member_user_id}",
            headers=_auth(owner_token),
        )
        assert r.status_code == 204

        # Task assignee should now be null
        r2 = await c.get(f"{BASE}/tasks/{task['id']}", headers=_auth(owner_token))
        assert r2.status_code == 200
        assert r2.json()["assignee_id"] is None


# ── assignee validation ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_to_member_ok() -> None:
    async with _client() as c:
        owner_data, _owner_email = await _make_user(c, "asgn_owner")
        member_data, member_email = await _make_user(c, "asgn_member")
        owner_token: str = owner_data["access_token"]  # type: ignore[assignment]
        member_user2: dict[str, object] = member_data["user"]  # type: ignore[assignment]
        proj = await _create_project(c, owner_token)
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": member_email, "role": "member"},
            headers=_auth(owner_token),
        )
        task = await _create_task(
            c,
            owner_token,
            str(proj["id"]),
            assignee_id=str(member_user2["id"]),
        )
        assert task["assignee_id"] == str(member_user2["id"])
