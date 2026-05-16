from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskPriority, TaskStatus

_SORTABLE: dict[str, Any] = {
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "due_date": Task.due_date,
    "priority": Task.priority,
    "title": Task.title,
}

_PRIORITY_ORDER = {
    TaskPriority.CRITICAL: 4,
    TaskPriority.HIGH: 3,
    TaskPriority.MEDIUM: 2,
    TaskPriority.LOW: 1,
}


def _sort_cols(sort: str | None) -> list[Any]:
    if not sort:
        return [Task.created_at.desc()]
    cols = []
    for part in sort.split(","):
        part = part.strip()
        desc = part.startswith("-")
        key = part.lstrip("-")
        col = _SORTABLE.get(key)
        if col is not None:
            cols.append(col.desc() if desc else col.asc())
    return cols or [Task.created_at.desc()]


async def create(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    creator_id: uuid.UUID,
    title: str,
    description: str = "",
    priority: TaskPriority = TaskPriority.MEDIUM,
    assignee_id: uuid.UUID | None = None,
    due_date: date | None = None,
) -> Task:
    task = Task(
        project_id=project_id,
        creator_id=creator_id,
        title=title,
        description=description,
        priority=priority,
        assignee_id=assignee_id,
        due_date=due_date,
        status=TaskStatus.TODO,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_by_id(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.assignee))
        .where(Task.id == task_id, Task.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def list_for_project(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    page: int = 1,
    size: int = 20,
    status: list[TaskStatus] | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: list[TaskPriority] | None = None,
    due_before: date | None = None,
    q: str | None = None,
    sort: str | None = None,
) -> tuple[list[Task], int]:
    size = min(size, 100)
    base = select(Task).where(Task.project_id == project_id, Task.deleted_at.is_(None))
    if status:
        base = base.where(Task.status.in_(status))
    if assignee_id is not None:
        base = base.where(Task.assignee_id == assignee_id)
    if priority:
        base = base.where(Task.priority.in_(priority))
    if due_before is not None:
        base = base.where(Task.due_date < due_before)
    if q:
        base = base.where(Task.title.ilike(f"%{q}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    items_q = (
        base.options(selectinload(Task.assignee))
        .order_by(*_sort_cols(sort))
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(items_q)).scalars().all()
    return list(rows), total


async def update_fields(
    db: AsyncSession,
    *,
    task: Task,
    title: str | None = None,
    description: str | None = None,
    priority: TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    due_date: date | None = None,
    clear_assignee: bool = False,
) -> Task:
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if priority is not None:
        task.priority = priority
    if clear_assignee:
        task.assignee_id = None
    elif assignee_id is not None:
        task.assignee_id = assignee_id
    if due_date is not None:
        task.due_date = due_date
    await db.flush()
    await db.refresh(task)
    return task


async def set_status(
    db: AsyncSession,
    *,
    task: Task,
    new_status: TaskStatus,
) -> Task:
    task.status = new_status
    task.completed_at = datetime.now(UTC) if new_status == TaskStatus.DONE else None
    await db.flush()
    await db.refresh(task)
    return task


async def soft_delete(db: AsyncSession, *, task: Task) -> None:
    task.deleted_at = datetime.now(UTC)
    await db.flush()


async def null_assignee_for_user(
    db: AsyncSession, *, project_id: uuid.UUID, user_id: uuid.UUID
) -> int:
    result = await db.execute(
        update(Task)
        .where(
            Task.project_id == project_id,
            Task.assignee_id == user_id,
            Task.deleted_at.is_(None),
        )
        .values(assignee_id=None)
        .returning(Task.id)
    )
    rows = result.fetchall()
    return len(rows)
