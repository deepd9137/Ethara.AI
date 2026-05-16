"""Direct service-layer tests for task_service for accurate branch coverage."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.middleware.exceptions import BusinessError
from app.models.project_member import ProjectRole
from app.models.task import TaskStatus
from app.models.user import User
from app.repositories import user_repo
from app.schemas.projects import ProjectCreate
from app.schemas.tasks import TaskCreate, TaskUpdate
from app.services import member_service, project_service, task_service


async def _create_user(db: AsyncSession, prefix: str = "u") -> User:
    email = f"{prefix}+{uuid.uuid4().hex[:8]}@tsvc.example"
    return await user_repo.create(db, email=email, name="Test", password_hash=b"hash")


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


async def _setup_project_with_member(
    db: AsyncSession,
) -> tuple[User, User, object]:
    owner = await _create_user(db, "owner")
    member_user = await _create_user(db, "member")
    proj = await project_service.create(
        db,
        user=owner,
        payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}"),
    )
    await member_service.invite(
        db,
        project=proj,
        email=member_user.email,
        role=ProjectRole.MEMBER,
        inviter=owner,
    )
    return owner, member_user, proj


# ── create ────────────────────────────────────────────────────────────────────


async def test_service_create_task_ok(db: AsyncSession) -> None:
    owner = await _create_user(db, "ct")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db,
        project=proj,
        actor=owner,
        payload=TaskCreate(title="My Task"),
    )
    assert task.title == "My Task"
    assert task.status == TaskStatus.TODO
    assert task.creator_id == owner.id


async def test_service_create_task_non_member_assignee_raises_422(
    db: AsyncSession,
) -> None:
    owner = await _create_user(db, "ctna")
    stranger = await _create_user(db, "ctna_str")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await task_service.create(
            db,
            project=proj,
            actor=owner,
            payload=TaskCreate(title="My Task", assignee_id=stranger.id),
        )
    assert exc_info.value.code == "ASSIGNEE_NOT_MEMBER"


# ── get_for_project ───────────────────────────────────────────────────────────


async def test_service_get_for_project_wrong_project_raises_404(
    db: AsyncSession,
) -> None:
    owner = await _create_user(db, "gfp")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    with pytest.raises(BusinessError) as exc_info:
        await task_service.get_for_project(db, project_id=uuid.uuid4(), task_id=task.id)
    assert exc_info.value.code == "TASK_NOT_FOUND"


# ── FSM transitions ───────────────────────────────────────────────────────────


async def test_service_fsm_allowed_transition(db: AsyncSession) -> None:
    owner = await _create_user(db, "fsm1")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    updated = await task_service.transition_status(
        db, task=task, new_status=TaskStatus.IN_PROGRESS, actor=owner
    )
    assert updated.status == TaskStatus.IN_PROGRESS


async def test_service_fsm_rejected_transition_raises_422(db: AsyncSession) -> None:
    owner = await _create_user(db, "fsm2")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    with pytest.raises(BusinessError) as exc_info:
        await task_service.transition_status(
            db, task=task, new_status=TaskStatus.DONE, actor=owner
        )
    assert exc_info.value.code == "INVALID_TRANSITION"
    assert exc_info.value.status_code == 422


async def test_service_fsm_done_sets_completed_at(db: AsyncSession) -> None:
    owner = await _create_user(db, "fsmdone")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    for status in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE):
        task = await task_service.transition_status(
            db, task=task, new_status=status, actor=owner
        )
    assert task.completed_at is not None


async def test_service_fsm_reopen_clears_completed_at(db: AsyncSession) -> None:
    owner = await _create_user(db, "fsmreopen")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    for status in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE):
        task = await task_service.transition_status(
            db, task=task, new_status=status, actor=owner
        )
    task = await task_service.transition_status(
        db, task=task, new_status=TaskStatus.IN_REVIEW, actor=owner
    )
    assert task.completed_at is None


# ── optimistic concurrency ────────────────────────────────────────────────────


async def test_service_if_match_mismatch_raises_412(db: AsyncSession) -> None:
    owner = await _create_user(db, "ifm")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    stale_ts = datetime.now(UTC) - timedelta(hours=1)
    with pytest.raises(BusinessError) as exc_info:
        await task_service.update(
            db,
            task=task,
            payload=TaskUpdate(title="Changed"),
            actor=owner,
            if_match=stale_ts,
        )
    assert exc_info.value.code == "PRECONDITION_FAILED"
    assert exc_info.value.status_code == 412


async def test_service_if_match_matching_allows_update(db: AsyncSession) -> None:
    owner = await _create_user(db, "ifmok")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    updated = await task_service.update(
        db,
        task=task,
        payload=TaskUpdate(title="Changed"),
        actor=owner,
        if_match=task.updated_at,
    )
    assert updated.title == "Changed"


# ── assignee validation ───────────────────────────────────────────────────────


async def test_service_update_assignee_to_non_member_raises_422(
    db: AsyncSession,
) -> None:
    owner, _member, proj = await _setup_project_with_member(db)
    stranger = await _create_user(db, "str")
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")  # type: ignore[arg-type]
    )
    with pytest.raises(BusinessError) as exc_info:
        await task_service.update(
            db,
            task=task,
            payload=TaskUpdate(assignee_id=stranger.id),
            actor=owner,
        )
    assert exc_info.value.code == "ASSIGNEE_NOT_MEMBER"


# ── null assignments ──────────────────────────────────────────────────────────


async def test_service_null_assignments_on_member_removal(db: AsyncSession) -> None:
    owner, member_user, proj = await _setup_project_with_member(db)
    task = await task_service.create(
        db,
        project=proj,  # type: ignore[arg-type]
        actor=owner,
        payload=TaskCreate(title="My Task", assignee_id=member_user.id),
    )
    assert task.assignee_id == member_user.id

    await member_service.remove_member(
        db, project=proj, target_user_id=member_user.id, actor=owner  # type: ignore[arg-type]
    )

    from app.repositories import tasks_repo

    refreshed = await tasks_repo.get_by_id(db, task.id)
    assert refreshed is not None
    assert refreshed.assignee_id is None


# ── soft delete ───────────────────────────────────────────────────────────────


async def test_service_soft_delete_hides_task(db: AsyncSession) -> None:
    owner = await _create_user(db, "sdel")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    await task_service.soft_delete(db, task=task, actor=owner)

    from app.repositories import tasks_repo

    result = await tasks_repo.get_by_id(db, task.id)
    assert result is None


# ── can_edit_task / can_delete_task helpers ───────────────────────────────────


async def test_can_edit_task_admin(db: AsyncSession) -> None:
    owner = await _create_user(db, "ceta")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    other = await _create_user(db, "ceta_other")
    assert task_service.can_edit_task(task, other, is_admin=True)


async def test_can_edit_task_creator(db: AsyncSession) -> None:
    owner = await _create_user(db, "cetc")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    assert task_service.can_edit_task(task, owner, is_admin=False)


async def test_can_edit_task_non_creator_non_admin_returns_false(
    db: AsyncSession,
) -> None:
    owner = await _create_user(db, "cetnc")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    other = await _create_user(db, "cetnc_other")
    assert not task_service.can_edit_task(task, other, is_admin=False)


async def test_can_delete_task_non_creator_returns_false(db: AsyncSession) -> None:
    owner = await _create_user(db, "cdtnc")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}")
    )
    task = await task_service.create(
        db, project=proj, actor=owner, payload=TaskCreate(title="My Task")
    )
    other = await _create_user(db, "cdtnc_other")
    assert not task_service.can_delete_task(task, other, is_admin=False)
