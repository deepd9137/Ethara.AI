from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.rbac import require_project_member
from app.db.session import get_db
from app.middleware.exceptions import BusinessError
from app.models.project_member import ProjectMember, ProjectRole
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.repositories import projects_repo, tasks_repo
from app.schemas.tasks import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import task_service

router = APIRouter()


def _parse_if_match(if_match: str | None) -> datetime | None:
    if if_match is None:
        return None
    try:
        return datetime.fromisoformat(if_match.strip('"'))
    except ValueError:
        return None


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=201,
)
async def create_task(
    project_id: uuid.UUID,
    payload: TaskCreate,
    member: Annotated[ProjectMember, Depends(require_project_member)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    task = await task_service.create(db, project=project, actor=user, payload=payload)
    return TaskResponse.model_validate(task)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=TaskListResponse,
)
async def list_tasks(
    project_id: uuid.UUID,
    _member: Annotated[ProjectMember, Depends(require_project_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Annotated[str | None, Query()] = None,
    assignee_id: Annotated[uuid.UUID | None, Query()] = None,
    priority: Annotated[str | None, Query()] = None,
    due_before: Annotated[datetime | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str | None, Query()] = None,
) -> TaskListResponse:
    status_list: list[TaskStatus] | None = None
    if status:
        status_list = [TaskStatus(s.strip()) for s in status.split(",") if s.strip()]

    priority_list: list[TaskPriority] | None = None
    if priority:
        priority_list = [
            TaskPriority(p.strip()) for p in priority.split(",") if p.strip()
        ]

    due_before_date = due_before.date() if due_before else None

    items, total = await tasks_repo.list_for_project(
        db,
        project_id=project_id,
        page=page,
        size=size,
        status=status_list,
        assignee_id=assignee_id,
        priority=priority_list,
        due_before=due_before_date,
        q=q,
        sort=sort,
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    task = await tasks_repo.get_by_id(db, task_id)
    if task is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)
    # Verify caller is a member of the task's project
    from app.repositories import project_members_repo

    member = await project_members_repo.get(
        db, project_id=task.project_id, user_id=user.id
    )
    if member is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)
    return TaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> TaskResponse:
    task = await tasks_repo.get_by_id(db, task_id)
    if task is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)

    from app.repositories import project_members_repo

    member = await project_members_repo.get(
        db, project_id=task.project_id, user_id=user.id
    )
    if member is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)

    is_admin = member.role == ProjectRole.ADMIN
    if not task_service.can_edit_task(task, user, is_admin):
        raise BusinessError(
            "FORBIDDEN",
            "Only admins, the creator, or the assignee can edit this task",
            status_code=403,
        )

    updated = await task_service.update(
        db,
        task=task,
        payload=payload,
        actor=user,
        if_match=_parse_if_match(if_match),
    )
    return TaskResponse.model_validate(updated)


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def transition_task_status(
    task_id: uuid.UUID,
    payload: TaskStatusUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> TaskResponse:
    task = await tasks_repo.get_by_id(db, task_id)
    if task is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)

    from app.repositories import project_members_repo

    member = await project_members_repo.get(
        db, project_id=task.project_id, user_id=user.id
    )
    if member is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)

    updated = await task_service.transition_status(
        db,
        task=task,
        new_status=payload.status,
        actor=user,
        if_match=_parse_if_match(if_match),
    )
    return TaskResponse.model_validate(updated)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    task = await tasks_repo.get_by_id(db, task_id)
    if task is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)

    from app.repositories import project_members_repo

    member = await project_members_repo.get(
        db, project_id=task.project_id, user_id=user.id
    )
    if member is None:
        raise BusinessError("TASK_NOT_FOUND", "Task not found", status_code=404)

    is_admin = member.role == ProjectRole.ADMIN
    if not task_service.can_delete_task(task, user, is_admin):
        raise BusinessError(
            "FORBIDDEN",
            "Only admins or the task creator can delete this task",
            status_code=403,
        )

    await task_service.soft_delete(db, task=task, actor=user)
    return Response(status_code=204)
