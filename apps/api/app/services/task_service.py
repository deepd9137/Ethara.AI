from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.exceptions import BusinessError
from app.models.project import Project
from app.models.task import ALLOWED_TRANSITIONS, Task, TaskStatus
from app.models.user import User
from app.repositories import project_members_repo, tasks_repo
from app.schemas.tasks import TaskCreate, TaskUpdate
from app.services import activity_service


async def _assert_assignee_is_member(
    db: AsyncSession, project_id: uuid.UUID, assignee_id: uuid.UUID
) -> None:
    member = await project_members_repo.get(
        db, project_id=project_id, user_id=assignee_id
    )
    if member is None:
        raise BusinessError(
            "ASSIGNEE_NOT_MEMBER",
            "Assignee must be an active project member",
            status_code=422,
        )


async def create(
    db: AsyncSession,
    *,
    project: Project,
    actor: User,
    payload: TaskCreate,
) -> Task:
    if payload.assignee_id is not None:
        await _assert_assignee_is_member(db, project.id, payload.assignee_id)

    task = await tasks_repo.create(
        db,
        project_id=project.id,
        creator_id=actor.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
    )
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=project.id,
        entity_type="task",
        entity_id=task.id,
        action="TASK_CREATED",
        metadata={"title": task.title},
    )
    await db.commit()
    return task


async def get_for_project(
    db: AsyncSession, *, project_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    task = await tasks_repo.get_by_id(db, task_id)
    if task is None or task.project_id != project_id:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)
    return task


async def update(
    db: AsyncSession,
    *,
    task: Task,
    payload: TaskUpdate,
    actor: User,
    if_match: datetime | None = None,
) -> Task:
    if if_match is not None and task.updated_at.replace(
        tzinfo=None
    ) != if_match.replace(tzinfo=None):
        raise BusinessError(
            "PRECONDITION_FAILED",
            "Task was modified by another request",
            status_code=412,
            details={"current_updated_at": task.updated_at.isoformat()},
        )

    if payload.assignee_id is not None:
        await _assert_assignee_is_member(db, task.project_id, payload.assignee_id)

    updated = await tasks_repo.update_fields(
        db,
        task=task,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
    )
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=task.project_id,
        entity_type="task",
        entity_id=task.id,
        action="TASK_UPDATED",
        metadata={
            k: v
            for k, v in {
                "title": payload.title,
                "priority": payload.priority.value if payload.priority else None,
                "assignee_id": (
                    str(payload.assignee_id) if payload.assignee_id else None
                ),
            }.items()
            if v is not None
        },
    )
    await db.commit()
    return updated


async def transition_status(
    db: AsyncSession,
    *,
    task: Task,
    new_status: TaskStatus,
    actor: User,
    if_match: datetime | None = None,
) -> Task:
    if if_match is not None and task.updated_at.replace(
        tzinfo=None
    ) != if_match.replace(tzinfo=None):
        raise BusinessError(
            "PRECONDITION_FAILED",
            "Task was modified by another request",
            status_code=412,
            details={"current_updated_at": task.updated_at.isoformat()},
        )

    allowed = ALLOWED_TRANSITIONS.get(task.status, set())
    if new_status not in allowed:
        raise BusinessError(
            "INVALID_TRANSITION",
            f"Cannot transition from {task.status} to {new_status}",
            status_code=422,
            details={"allowed": [s.value for s in allowed]},
        )

    updated = await tasks_repo.set_status(db, task=task, new_status=new_status)
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=task.project_id,
        entity_type="task",
        entity_id=task.id,
        action="TASK_STATUS_CHANGED",
        metadata={"from": task.status.value, "to": new_status.value},
    )
    await db.commit()
    return updated


async def soft_delete(
    db: AsyncSession,
    *,
    task: Task,
    actor: User,
) -> None:
    await tasks_repo.soft_delete(db, task=task)
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=task.project_id,
        entity_type="task",
        entity_id=task.id,
        action="TASK_DELETED",
        metadata={},
    )
    await db.commit()


async def null_assignments_for_removed_member(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    count = await tasks_repo.null_assignee_for_user(
        db, project_id=project_id, user_id=user_id
    )
    if count > 0:
        await activity_service.log(
            db,
            actor_id=actor_id,
            project_id=project_id,
            entity_type="member",
            entity_id=user_id,
            action="ASSIGNMENTS_NULLED",
            metadata={"count": count},
        )


def can_edit_task(task: Task, actor: User, is_admin: bool) -> bool:
    return is_admin or task.creator_id == actor.id or task.assignee_id == actor.id


def can_delete_task(task: Task, actor: User, is_admin: bool) -> bool:
    return is_admin or task.creator_id == actor.id
