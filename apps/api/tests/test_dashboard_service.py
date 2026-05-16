"""Direct service-layer tests for dashboard_service.

Tests run in the same coroutine context as the service functions, yielding
accurate branch coverage (cf. CLAUDE.md Coverage quirk section).
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.project_member import ProjectRole
from app.models.task import TaskStatus
from app.models.user import User
from app.repositories import project_members_repo, tasks_repo, user_repo
from app.schemas.projects import ProjectCreate
from app.schemas.tasks import TaskCreate
from app.services import (
    activity_service,
    dashboard_service,
    project_service,
    task_service,
)


async def _make_user(db: AsyncSession, prefix: str = "u") -> User:
    email = f"{prefix}+{uuid.uuid4().hex[:8]}@dash.example"
    return await user_repo.create(db, email=email, name="Dash User", password_hash=b"h")


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


# ── get_stats ─────────────────────────────────────────────────────────────────


async def test_stats_empty_for_new_user(db: AsyncSession) -> None:
    user = await _make_user(db, "stats_empty")
    result = await dashboard_service.get_stats(db, user_id=user.id)
    assert result.open == 0
    assert result.overdue == 0
    assert result.due_this_week == 0


async def test_stats_counts_open_tasks(db: AsyncSession) -> None:
    owner = await _make_user(db, "stats_open")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"StatsProj-{uuid.uuid4().hex[:6]}")
    )
    for i in range(2):
        await task_service.create(
            db, project=proj, actor=owner, payload=TaskCreate(title=f"Task{i}")
        )
    # Transition one task to done — it should be excluded from open count
    done_task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="Done task")
    )
    done_task = await task_service.transition_status(
        db, task=done_task, new_status=TaskStatus.IN_PROGRESS, actor=owner
    )
    done_task = await task_service.transition_status(
        db, task=done_task, new_status=TaskStatus.IN_REVIEW, actor=owner
    )
    await task_service.transition_status(
        db, task=done_task, new_status=TaskStatus.DONE, actor=owner
    )

    result = await dashboard_service.get_stats(db, user_id=owner.id)
    assert result.open == 2


async def test_stats_overdue(db: AsyncSession) -> None:
    owner = await _make_user(db, "stats_overdue")
    proj = await project_service.create(
        db,
        user=owner,
        payload=ProjectCreate(name=f"OverdueProj-{uuid.uuid4().hex[:6]}"),
    )
    # Bypass TaskCreate validator (rejects past dates) by writing directly to the repo.
    # Use 2 days ago to avoid UTC/local timezone boundary causing CURRENT_DATE to match.
    overdue_date = date.today() - timedelta(days=2)
    overdue_task = await tasks_repo.create(
        db,
        project_id=proj.id,
        creator_id=owner.id,
        title="Overdue open",
        due_date=overdue_date,
    )
    await activity_service.log(
        db,
        actor_id=owner.id,
        project_id=proj.id,
        entity_type="task",
        entity_id=overdue_task.id,
        action="TASK_CREATED",
        metadata={"title": overdue_task.title},
    )
    await db.commit()

    result = await dashboard_service.get_stats(db, user_id=owner.id)
    assert result.overdue == 1
    assert result.open == 1


async def test_stats_due_this_week(db: AsyncSession) -> None:
    owner = await _make_user(db, "stats_week")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"WeekProj-{uuid.uuid4().hex[:6]}")
    )
    in_6_days = date.today() + timedelta(days=6)
    in_8_days = date.today() + timedelta(days=8)
    await task_service.create(
        db,
        project=proj,
        actor=owner,
        payload=TaskCreate(title="Soon", due_date=in_6_days),
    )
    await task_service.create(
        db,
        project=proj,
        actor=owner,
        payload=TaskCreate(title="Later", due_date=in_8_days),
    )
    result = await dashboard_service.get_stats(db, user_id=owner.id)
    assert result.due_this_week == 1


async def test_stats_only_counts_member_projects(db: AsyncSession) -> None:
    owner = await _make_user(db, "stats_member_owner")
    other = await _make_user(db, "stats_member_other")
    proj = await project_service.create(
        db,
        user=owner,
        payload=ProjectCreate(name=f"PrivateProj-{uuid.uuid4().hex[:6]}"),
    )
    await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="Owner task")
    )
    result = await dashboard_service.get_stats(db, user_id=other.id)
    assert result.open == 0


# ── get_my_tasks ──────────────────────────────────────────────────────────────


async def test_my_tasks_empty_for_new_user(db: AsyncSession) -> None:
    user = await _make_user(db, "mytasks_empty")
    result = await dashboard_service.get_my_tasks(db, user_id=user.id)
    assert result.items == []
    assert result.total == 0


async def test_my_tasks_returns_assigned_tasks(db: AsyncSession) -> None:
    owner = await _make_user(db, "mytasks_owner")
    assignee = await _make_user(db, "mytasks_assignee")
    proj = await project_service.create(
        db,
        user=owner,
        payload=ProjectCreate(name=f"MyTasksProj-{uuid.uuid4().hex[:6]}"),
    )
    # Make assignee a project member so the task_service.create check passes
    await project_members_repo.add(
        db,
        project_id=proj.id,
        user_id=assignee.id,
        role=ProjectRole.MEMBER,
        invited_by=owner.id,
    )
    await task_service.create(
        db,
        project=proj,
        actor=owner,
        payload=TaskCreate(title="Assigned task", assignee_id=assignee.id),
    )
    await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="Unassigned task")
    )
    result = await dashboard_service.get_my_tasks(db, user_id=assignee.id)
    assert result.total == 1
    assert result.items[0].title == "Assigned task"


async def test_my_tasks_excludes_done(db: AsyncSession) -> None:
    owner = await _make_user(db, "mytasks_done_owner")
    assignee = await _make_user(db, "mytasks_done_assignee")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"DoneProj-{uuid.uuid4().hex[:6]}")
    )
    await project_members_repo.add(
        db,
        project_id=proj.id,
        user_id=assignee.id,
        role=ProjectRole.MEMBER,
        invited_by=owner.id,
    )
    task = await task_service.create(
        db,
        project=proj,
        actor=owner,
        payload=TaskCreate(title="Will be done", assignee_id=assignee.id),
    )
    for status in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE):
        task = await task_service.transition_status(
            db, task=task, new_status=status, actor=owner
        )
    result = await dashboard_service.get_my_tasks(db, user_id=assignee.id)
    assert result.total == 0


async def test_my_tasks_includes_project_info(db: AsyncSession) -> None:
    owner = await _make_user(db, "mytasks_proj_info")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"ProjInfo-{uuid.uuid4().hex[:6]}")
    )
    await task_service.create(
        db,
        project=proj,
        actor=owner,
        payload=TaskCreate(title="Info task", assignee_id=owner.id),
    )
    result = await dashboard_service.get_my_tasks(db, user_id=owner.id)
    assert result.total == 1
    assert result.items[0].project.id == proj.id
    assert result.items[0].project.name == proj.name


# ── get_recent_activity ───────────────────────────────────────────────────────


async def test_recent_activity_empty_for_new_user(db: AsyncSession) -> None:
    user = await _make_user(db, "activity_empty")
    result = await dashboard_service.get_recent_activity(db, user_id=user.id)
    assert result.items == []
    assert result.total == 0


async def test_recent_activity_shows_project_events(db: AsyncSession) -> None:
    owner = await _make_user(db, "activity_owner")
    proj = await project_service.create(
        db,
        user=owner,
        payload=ProjectCreate(name=f"ActivityProj-{uuid.uuid4().hex[:6]}"),
    )
    await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="Activity task")
    )
    result = await dashboard_service.get_recent_activity(db, user_id=owner.id)
    assert result.total >= 1
    assert result.items[0].project_id == proj.id


async def test_recent_activity_respects_member_scope(db: AsyncSession) -> None:
    owner = await _make_user(db, "activity_scope_owner")
    outsider = await _make_user(db, "activity_scope_outsider")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"ScopeProj-{uuid.uuid4().hex[:6]}")
    )
    await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="Scoped task")
    )
    result = await dashboard_service.get_recent_activity(db, user_id=outsider.id)
    assert result.total == 0
