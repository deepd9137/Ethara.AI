import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.exceptions import BusinessError
from app.models.project import Project
from app.models.project_member import ProjectRole
from app.models.user import User
from app.repositories import project_members_repo, projects_repo
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.services import activity_service


async def create(
    db: AsyncSession,
    *,
    user: User,
    payload: ProjectCreate,
) -> Project:
    if await projects_repo.exists_by_name(db, owner_id=user.id, name=payload.name):
        raise BusinessError(
            "PROJECT_NAME_TAKEN", "Project name already in use", status_code=409
        )

    project = await projects_repo.create(
        db, owner_id=user.id, name=payload.name, description=payload.description
    )
    await project_members_repo.add(
        db,
        project_id=project.id,
        user_id=user.id,
        role=ProjectRole.ADMIN,
        invited_by=None,
    )
    await activity_service.log(
        db,
        actor_id=user.id,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="PROJECT_CREATED",
        metadata={"name": project.name},
    )
    await db.commit()
    return project


async def list_for_user(
    db: AsyncSession,
    *,
    user: User,
    page: int = 1,
    size: int = 20,
    q: str | None = None,
    sort: str | None = None,
) -> tuple[list[Project], int]:
    return await projects_repo.list_for_user(
        db, user_id=user.id, page=page, size=size, q=q, sort=sort
    )


async def get_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    member = await project_members_repo.get(db, project_id=project_id, user_id=user_id)
    if member is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    return project


async def update(
    db: AsyncSession,
    *,
    project: Project,
    payload: ProjectUpdate,
    actor: User,
) -> Project:
    if (
        payload.name is not None
        and payload.name != project.name
        and await projects_repo.exists_by_name(
            db, owner_id=project.owner_id, name=payload.name
        )
    ):
        raise BusinessError(
            "PROJECT_NAME_TAKEN", "Project name already in use", status_code=409
        )

    updated = await projects_repo.update(
        db, project=project, name=payload.name, description=payload.description
    )
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="PROJECT_UPDATED",
        metadata={
            k: v
            for k, v in {
                "name": payload.name,
                "description": payload.description,
            }.items()
            if v is not None
        },
    )
    await db.commit()
    return updated


async def soft_delete(
    db: AsyncSession,
    *,
    project: Project,
    actor: User,
) -> None:
    await projects_repo.soft_delete(db, project=project)
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="PROJECT_DELETED",
        metadata={},
    )
    await db.commit()


async def transfer_owner(
    db: AsyncSession,
    *,
    project: Project,
    new_owner_id: uuid.UUID,
    actor: User,
) -> Project:
    if project.owner_id != actor.id:
        raise BusinessError(
            "FORBIDDEN",
            "Only the project owner can transfer ownership",
            status_code=403,
        )
    if new_owner_id == project.owner_id:
        return project

    new_owner_member = await project_members_repo.get(
        db, project_id=project.id, user_id=new_owner_id
    )
    if new_owner_member is None:
        raise BusinessError(
            "MEMBER_NOT_FOUND",
            "New owner must be an existing project member",
            status_code=404,
        )
    # Ensure new owner becomes admin
    if new_owner_member.role != ProjectRole.ADMIN:
        await project_members_repo.update_role(
            db, member=new_owner_member, role=ProjectRole.ADMIN
        )

    updated = await projects_repo.set_owner(
        db, project=project, new_owner_id=new_owner_id
    )
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="OWNER_TRANSFERRED",
        metadata={
            "previous_owner_id": str(actor.id),
            "new_owner_id": str(new_owner_id),
        },
    )
    await db.commit()
    return updated
