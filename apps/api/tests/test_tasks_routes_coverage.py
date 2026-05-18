"""Targeted route-layer tests for app/api/routes/tasks.py coverage gaps.

These exercise 404 / non-member / malformed-input branches that the
existing test_tasks.py (which focuses on happy paths and FSM/RBAC matrix)
does not hit. Uses the shared api_client / make_user fixtures from conftest.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import MakeUser, bearer

PROJECTS_URL = "/v1/projects"


# ---------- helpers (kept tiny; full helpers will land in factories commit) ----------


async def _create_project(client: AsyncClient, token: str) -> dict[str, Any]:
    r = await client.post(
        PROJECTS_URL, json={"name": f"P-{uuid.uuid4().hex[:6]}"}, headers=bearer(token)
    )
    assert r.status_code == 201, r.text
    data: dict[str, Any] = r.json()
    return data


async def _create_task(
    client: AsyncClient, token: str, project_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": "Test task", "priority": "medium"}
    payload.update(overrides)
    r = await client.post(
        f"{PROJECTS_URL}/{project_id}/tasks", json=payload, headers=bearer(token)
    )
    assert r.status_code == 201, r.text
    data: dict[str, Any] = r.json()
    return data


# ---------- 404 paths: task does not exist ----------


@pytest.mark.asyncio
async def test_get_task_unknown_id_returns_404(
    api_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    r = await api_client.get(f"/v1/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_task_unknown_id_returns_404(
    api_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    r = await api_client.patch(
        f"/v1/tasks/{uuid.uuid4()}", json={"title": "updated"}, headers=auth_headers
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_status_unknown_id_returns_404(
    api_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    r = await api_client.patch(
        f"/v1/tasks/{uuid.uuid4()}/status",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_task_unknown_id_returns_404(
    api_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    r = await api_client.delete(f"/v1/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TASK_NOT_FOUND"


# ---------- non-member 404: task exists but caller isn't in the project ----------


@pytest.mark.asyncio
async def test_patch_task_as_non_member_returns_404(
    api_client: AsyncClient, make_user: MakeUser
) -> None:
    _, _, owner_token = await make_user(prefix="owner")
    _, _, outsider_token = await make_user(prefix="outsider")
    proj = await _create_project(api_client, owner_token)
    task = await _create_task(api_client, owner_token, proj["id"])

    r = await api_client.patch(
        f"/v1/tasks/{task['id']}",
        json={"title": "hijacked"},
        headers=bearer(outsider_token),
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_status_as_non_member_returns_404(
    api_client: AsyncClient, make_user: MakeUser
) -> None:
    _, _, owner_token = await make_user(prefix="owner")
    _, _, outsider_token = await make_user(prefix="outsider")
    proj = await _create_project(api_client, owner_token)
    task = await _create_task(api_client, owner_token, proj["id"])

    r = await api_client.patch(
        f"/v1/tasks/{task['id']}/status",
        json={"status": "in_progress"},
        headers=bearer(outsider_token),
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_task_as_non_member_returns_404(
    api_client: AsyncClient, make_user: MakeUser
) -> None:
    _, _, owner_token = await make_user(prefix="owner")
    _, _, outsider_token = await make_user(prefix="outsider")
    proj = await _create_project(api_client, owner_token)
    task = await _create_task(api_client, owner_token, proj["id"])

    r = await api_client.delete(
        f"/v1/tasks/{task['id']}", headers=bearer(outsider_token)
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TASK_NOT_FOUND"


# ---------- malformed If-Match header ----------


@pytest.mark.asyncio
async def test_patch_task_malformed_if_match_is_ignored(
    api_client: AsyncClient, make_user: MakeUser
) -> None:
    """A non-ISO If-Match value parses to None and is silently skipped — update succeeds."""
    _, _, token = await make_user()
    proj = await _create_project(api_client, token)
    task = await _create_task(api_client, token, proj["id"])

    r = await api_client.patch(
        f"/v1/tasks/{task['id']}",
        json={"title": "updated"},
        headers={**bearer(token), "If-Match": "not-an-iso-timestamp"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "updated"


@pytest.mark.asyncio
async def test_patch_status_malformed_if_match_is_ignored(
    api_client: AsyncClient, make_user: MakeUser
) -> None:
    _, _, token = await make_user()
    proj = await _create_project(api_client, token)
    task = await _create_task(api_client, token, proj["id"])

    r = await api_client.patch(
        f"/v1/tasks/{task['id']}/status",
        json={"status": "in_progress"},
        headers={**bearer(token), "If-Match": "garbage"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_progress"


# ---------- list_tasks filters ----------


@pytest.mark.asyncio
async def test_list_tasks_priority_filter(
    api_client: AsyncClient, make_user: MakeUser
) -> None:
    _, _, token = await make_user()
    proj = await _create_project(api_client, token)
    await _create_task(api_client, token, proj["id"], title="low task", priority="low")
    await _create_task(api_client, token, proj["id"], title="hi task", priority="high")
    await _create_task(
        api_client, token, proj["id"], title="crit task", priority="critical"
    )

    r = await api_client.get(
        f"{PROJECTS_URL}/{proj['id']}/tasks?priority=high,critical",
        headers=bearer(token),
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    priorities = sorted(t["priority"] for t in items)
    assert priorities == ["critical", "high"]


@pytest.mark.asyncio
async def test_list_tasks_empty_status_filter_segments_ignored(
    api_client: AsyncClient, make_user: MakeUser
) -> None:
    """status=todo,, should drop empties and still match the single value."""
    _, _, token = await make_user()
    proj = await _create_project(api_client, token)
    await _create_task(api_client, token, proj["id"])

    r = await api_client.get(
        f"{PROJECTS_URL}/{proj['id']}/tasks?status=todo,,",
        headers=bearer(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1
