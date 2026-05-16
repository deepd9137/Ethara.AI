import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.middleware.exceptions import BusinessError
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.models.user import User


async def require_project_member(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMember:
    """Return the caller's ProjectMember row; 404 if not a member or project absent/deleted."""
    result = await db.execute(
        select(ProjectMember)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
            Project.deleted_at.is_(None),
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    return member


async def require_project_admin(
    member: ProjectMember = Depends(require_project_member),
) -> ProjectMember:
    """Return the member if they are an admin; 403 otherwise."""
    if member.role != ProjectRole.ADMIN:
        raise BusinessError("FORBIDDEN", "Admin role required", status_code=403)
    return member
