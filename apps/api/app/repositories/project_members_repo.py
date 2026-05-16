import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project_member import ProjectMember, ProjectRole


async def add(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role: ProjectRole,
    invited_by: uuid.UUID | None,
) -> ProjectMember:
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
    )
    db.add(member)
    await db.flush()
    return member


async def get(
    db: AsyncSession, *, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMember | None:
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_by_project(
    db: AsyncSession, *, project_id: uuid.UUID
) -> list[ProjectMember]:
    result = await db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .options(selectinload(ProjectMember.user))
        .order_by(ProjectMember.created_at.asc())
    )
    return list(result.scalars().all())


async def count_admins(db: AsyncSession, *, project_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).where(
            ProjectMember.project_id == project_id,
            ProjectMember.role == ProjectRole.ADMIN,
        )
    )
    return result.scalar_one()


async def update_role(
    db: AsyncSession, *, member: ProjectMember, role: ProjectRole
) -> ProjectMember:
    member.role = role
    await db.flush()
    return member


async def remove(db: AsyncSession, *, member: ProjectMember) -> None:
    await db.delete(member)
    await db.flush()
