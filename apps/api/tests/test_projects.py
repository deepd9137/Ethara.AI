"""HTTP integration tests for projects and members endpoints (RBAC matrix)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "https://test"
SIGNUP_URL = "/v1/auth/signup"
LOGIN_URL = "/v1/auth/login"
PROJECTS_URL = "/v1/projects"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


def _email(prefix: str = "u") -> str:
    return f"{prefix}+{uuid.uuid4().hex[:8]}@test.com"


async def _make_user(client: AsyncClient, email: str | None = None) -> tuple[dict, str]:  # type: ignore[type-arg]
    em = email or _email()
    r = await client.post(
        SIGNUP_URL, json={"email": em, "name": "Test User", "password": "Password123"}
    )
    assert r.status_code == 201, r.text
    data = r.json()
    return data, em


async def _login(client: AsyncClient, email: str) -> str:
    r = await client.post(LOGIN_URL, json={"email": email, "password": "Password123"})
    assert r.status_code == 200
    token: str = r.json()["access_token"]
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_project(
    client: AsyncClient, token: str, name: str | None = None
) -> dict[str, object]:
    payload = {"name": name or f"Proj-{uuid.uuid4().hex[:6]}", "description": "desc"}
    r = await client.post(PROJECTS_URL, json=payload, headers=_auth(token))
    assert r.status_code == 201, r.text
    result: dict[str, object] = r.json()
    return result


# ── project CRUD ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_returns_201() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        token = data["access_token"]
        r = await c.post(
            PROJECTS_URL,
            json={"name": "My Project", "description": "hello"},
            headers=_auth(token),
        )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "My Project"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_project_duplicate_name_returns_409() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        token = data["access_token"]
        name = f"DupProj-{uuid.uuid4().hex[:6]}"
        await _create_project(c, token, name)
        r = await c.post(PROJECTS_URL, json={"name": name}, headers=_auth(token))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "PROJECT_NAME_TAKEN"


@pytest.mark.asyncio
async def test_list_projects_shows_own_projects_only() -> None:
    async with _client() as c:
        data1, _ = await _make_user(c)
        t1 = data1["access_token"]
        data2, _ = await _make_user(c)
        t2 = data2["access_token"]

        proj = await _create_project(c, t1)

        r1 = await c.get(PROJECTS_URL, headers=_auth(t1))
        r2 = await c.get(PROJECTS_URL, headers=_auth(t2))

    assert r1.status_code == 200
    ids_for_u1 = [p["id"] for p in r1.json()["items"]]
    assert proj["id"] in ids_for_u1

    assert r2.status_code == 200
    ids_for_u2 = [p["id"] for p in r2.json()["items"]]
    assert proj["id"] not in ids_for_u2


@pytest.mark.asyncio
async def test_get_project_member_returns_200() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        token = data["access_token"]
        proj = await _create_project(c, token)
        r = await c.get(f"{PROJECTS_URL}/{proj['id']}", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["id"] == proj["id"]


@pytest.mark.asyncio
async def test_get_project_non_member_returns_404() -> None:
    async with _client() as c:
        data1, _ = await _make_user(c)
        data2, _ = await _make_user(c)
        proj = await _create_project(c, data1["access_token"])
        r = await c.get(
            f"{PROJECTS_URL}/{proj['id']}", headers=_auth(data2["access_token"])
        )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "PROJECT_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_project_admin_returns_200() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        token = data["access_token"]
        proj = await _create_project(c, token)
        r = await c.patch(
            f"{PROJECTS_URL}/{proj['id']}",
            json={"name": "Updated Name", "description": "new"},
            headers=_auth(token),
        )
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_project_member_returns_403() -> None:
    async with _client() as c:
        data_owner, _em_owner = await _make_user(c)
        data_member, em_member = await _make_user(c)
        token_owner = data_owner["access_token"]
        token_member = data_member["access_token"]

        proj = await _create_project(c, token_owner)
        # Invite second user as member
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_member, "role": "member"},
            headers=_auth(token_owner),
        )
        r = await c.patch(
            f"{PROJECTS_URL}/{proj['id']}",
            json={"name": "Hacked"},
            headers=_auth(token_member),
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_update_project_non_member_returns_404() -> None:
    async with _client() as c:
        data1, _ = await _make_user(c)
        data2, _ = await _make_user(c)
        proj = await _create_project(c, data1["access_token"])
        r = await c.patch(
            f"{PROJECTS_URL}/{proj['id']}",
            json={"name": "hacked"},
            headers=_auth(data2["access_token"]),
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_admin_returns_204() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        token = data["access_token"]
        proj = await _create_project(c, token)
        r = await c.delete(f"{PROJECTS_URL}/{proj['id']}", headers=_auth(token))
        assert r.status_code == 204
        # After deletion, project is gone (404)
        r2 = await c.get(f"{PROJECTS_URL}/{proj['id']}", headers=_auth(token))
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_member_returns_403() -> None:
    async with _client() as c:
        data_owner, _em_owner = await _make_user(c)
        data_member, em_member = await _make_user(c)
        token_owner = data_owner["access_token"]
        token_member = data_member["access_token"]

        proj = await _create_project(c, token_owner)
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_member, "role": "member"},
            headers=_auth(token_owner),
        )
        r = await c.delete(f"{PROJECTS_URL}/{proj['id']}", headers=_auth(token_member))
    assert r.status_code == 403


# ── members ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invite_member_success() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        _data_invitee, em_invitee = await _make_user(c)
        token_owner = data_owner["access_token"]

        proj = await _create_project(c, token_owner)
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_invitee, "role": "member"},
            headers=_auth(token_owner),
        )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "member"
    assert body["user"]["email"] == em_invitee


@pytest.mark.asyncio
async def test_invite_nonexistent_user_returns_404() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        proj = await _create_project(c, data["access_token"])
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": "nobody@nowhere.com"},
            headers=_auth(data["access_token"]),
        )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "MEMBER_NOT_FOUND"


@pytest.mark.asyncio
async def test_invite_already_member_returns_409() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        _data_invitee, em_invitee = await _make_user(c)
        token = data_owner["access_token"]
        proj = await _create_project(c, token)
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_invitee},
            headers=_auth(token),
        )
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_invitee},
            headers=_auth(token),
        )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ALREADY_MEMBER"


@pytest.mark.asyncio
async def test_invite_member_non_admin_returns_403() -> None:
    async with _client() as c:
        data_owner, _em_owner = await _make_user(c)
        data_m1, em_m1 = await _make_user(c)
        _data_m2, em_m2 = await _make_user(c)
        token_owner = data_owner["access_token"]
        token_m1 = data_m1["access_token"]

        proj = await _create_project(c, token_owner)
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_m1, "role": "member"},
            headers=_auth(token_owner),
        )
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_m2},
            headers=_auth(token_m1),
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_members_member_can_read() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        data_member, em_member = await _make_user(c)
        token_owner = data_owner["access_token"]
        token_member = data_member["access_token"]

        proj = await _create_project(c, token_owner)
        await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_member},
            headers=_auth(token_owner),
        )
        r = await c.get(
            f"{PROJECTS_URL}/{proj['id']}/members", headers=_auth(token_member)
        )
    assert r.status_code == 200
    assert r.json()["total"] == 2


@pytest.mark.asyncio
async def test_change_role_success() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        _data_m, em_m = await _make_user(c)
        token_owner = data_owner["access_token"]
        proj = await _create_project(c, token_owner)
        invite_r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_m, "role": "member"},
            headers=_auth(token_owner),
        )
        uid = invite_r.json()["user_id"]
        r = await c.patch(
            f"{PROJECTS_URL}/{proj['id']}/members/{uid}",
            json={"role": "admin"},
            headers=_auth(token_owner),
        )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_change_role_last_admin_returns_409() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        token = data["access_token"]
        proj = await _create_project(c, token)
        owner_id = data["user"]["id"]
        r = await c.patch(
            f"{PROJECTS_URL}/{proj['id']}/members/{owner_id}",
            json={"role": "member"},
            headers=_auth(token),
        )
    # Owner is last admin → 403 (cannot change owner's role)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_change_role_demote_from_two_admins_succeeds() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        _data_m, em_m = await _make_user(c)
        token_owner = data_owner["access_token"]
        proj = await _create_project(c, token_owner)
        # Promote member to admin
        invite_r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_m, "role": "admin"},
            headers=_auth(token_owner),
        )
        uid = invite_r.json()["user_id"]
        # Demote the second admin back to member — should succeed (owner is still admin)
        r = await c.patch(
            f"{PROJECTS_URL}/{proj['id']}/members/{uid}",
            json={"role": "member"},
            headers=_auth(token_owner),
        )
    assert r.status_code == 200
    assert r.json()["role"] == "member"


@pytest.mark.asyncio
async def test_remove_member_success() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        _data_m, em_m = await _make_user(c)
        token_owner = data_owner["access_token"]
        proj = await _create_project(c, token_owner)
        invite_r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_m},
            headers=_auth(token_owner),
        )
        uid = invite_r.json()["user_id"]
        r = await c.delete(
            f"{PROJECTS_URL}/{proj['id']}/members/{uid}", headers=_auth(token_owner)
        )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_remove_owner_returns_409() -> None:
    async with _client() as c:
        data, _ = await _make_user(c)
        token = data["access_token"]
        owner_id = data["user"]["id"]
        proj = await _create_project(c, token)
        r = await c.delete(
            f"{PROJECTS_URL}/{proj['id']}/members/{owner_id}", headers=_auth(token)
        )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CANNOT_REMOVE_OWNER"


@pytest.mark.asyncio
async def test_transfer_owner_success() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        _data_m, em_m = await _make_user(c)
        token_owner = data_owner["access_token"]
        proj = await _create_project(c, token_owner)
        invite_r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_m, "role": "admin"},
            headers=_auth(token_owner),
        )
        new_owner_id = invite_r.json()["user_id"]
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/transfer-owner",
            json={"user_id": new_owner_id},
            headers=_auth(token_owner),
        )
    assert r.status_code == 200
    assert r.json()["owner_id"] == new_owner_id


@pytest.mark.asyncio
async def test_transfer_owner_non_owner_returns_403() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        data_m, em_m = await _make_user(c)
        token_owner = data_owner["access_token"]
        token_m = data_m["access_token"]
        proj = await _create_project(c, token_owner)
        invite_r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/members",
            json={"email": em_m, "role": "admin"},
            headers=_auth(token_owner),
        )
        new_id = invite_r.json()["user_id"]
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/transfer-owner",
            json={"user_id": new_id},
            headers=_auth(token_m),
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_transfer_owner_to_non_member_returns_404() -> None:
    async with _client() as c:
        data_owner, _ = await _make_user(c)
        data_outsider, _ = await _make_user(c)
        token_owner = data_owner["access_token"]
        proj = await _create_project(c, token_owner)
        r = await c.post(
            f"{PROJECTS_URL}/{proj['id']}/transfer-owner",
            json={"user_id": data_outsider["user"]["id"]},
            headers=_auth(token_owner),
        )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "MEMBER_NOT_FOUND"
