import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.project import Project
from app.models.project_member import ProjectMember

_SORTABLE: dict[str, Any] = {
    "created_at": Project.created_at,
    "updated_at": Project.updated_at,
    "name": Project.name,
}


def _sort_cols(sort: str | None) -> list[Any]:
    if not sort:
        return [Project.created_at.desc()]
    cols = []
    for part in sort.split(","):
        part = part.strip()
        desc = part.startswith("-")
        key = part.lstrip("-")
        col = _SORTABLE.get(key)
        if col is not None:
            cols.append(col.desc() if desc else col.asc())
    return cols or [Project.created_at.desc()]


async def create(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    name: str,
    description: str = "",
) -> Project:
    project = Project(owner_id=owner_id, name=name, description=description)
    db.add(project)
    await db.flush()
    return project


async def get_by_id(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def exists_by_name(db: AsyncSession, *, owner_id: uuid.UUID, name: str) -> bool:
    result = await db.execute(
        select(func.count()).where(
            Project.owner_id == owner_id,
            Project.name == name,
            Project.deleted_at.is_(None),
        )
    )
    return (result.scalar_one() or 0) > 0


async def list_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    size: int = 20,
    q: str | None = None,
    sort: str | None = None,
) -> tuple[list[Project], int]:
    pm = aliased(ProjectMember)
    base = (
        select(Project)
        .join(pm, (pm.project_id == Project.id) & (pm.user_id == user_id))
        .where(Project.deleted_at.is_(None))
    )
    if q:
        base = base.where(Project.name.ilike(f"%{q}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    items_q = base.order_by(*_sort_cols(sort)).offset((page - 1) * size).limit(size)
    rows = (await db.execute(items_q)).scalars().all()
    return list(rows), total


async def update(
    db: AsyncSession,
    *,
    project: Project,
    name: str | None = None,
    description: str | None = None,
) -> Project:
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    await db.flush()
    await db.refresh(project)
    return project


async def soft_delete(db: AsyncSession, *, project: Project) -> None:
    from datetime import UTC, datetime

    project.deleted_at = datetime.now(UTC)
    await db.flush()


async def set_owner(
    db: AsyncSession, *, project: Project, new_owner_id: uuid.UUID
) -> Project:
    project.owner_id = new_owner_id
    await db.flush()
    await db.refresh(project)
    return project
