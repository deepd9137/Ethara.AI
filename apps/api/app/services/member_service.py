import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.exceptions import BusinessError
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.models.user import User
from app.repositories import project_members_repo, user_repo
from app.services import activity_service, task_service


async def invite(
    db: AsyncSession,
    *,
    project: Project,
    email: str,
    role: ProjectRole,
    inviter: User,
) -> ProjectMember:
    invitee = await user_repo.get_by_email(db, email)
    if invitee is None:
        raise BusinessError(
            "MEMBER_NOT_FOUND", "No user with that email", status_code=404
        )

    if invitee.id == inviter.id:
        raise BusinessError("ALREADY_MEMBER", "Cannot invite yourself", status_code=409)

    existing = await project_members_repo.get(
        db, project_id=project.id, user_id=invitee.id
    )
    if existing is not None:
        raise BusinessError(
            "ALREADY_MEMBER", "User is already a member", status_code=409
        )

    member = await project_members_repo.add(
        db,
        project_id=project.id,
        user_id=invitee.id,
        role=role,
        invited_by=inviter.id,
    )
    await activity_service.log(
        db,
        actor_id=inviter.id,
        project_id=project.id,
        entity_type="member",
        entity_id=invitee.id,
        action="MEMBER_INVITED",
        metadata={"email": email, "role": role.value},
    )
    await db.commit()
    return member


async def list_members(
    db: AsyncSession, *, project_id: uuid.UUID
) -> list[ProjectMember]:
    return await project_members_repo.list_by_project(db, project_id=project_id)


async def change_role(
    db: AsyncSession,
    *,
    project: Project,
    target_user_id: uuid.UUID,
    new_role: ProjectRole,
    actor: User,
) -> ProjectMember:
    member = await project_members_repo.get(
        db, project_id=project.id, user_id=target_user_id
    )
    if member is None:
        raise BusinessError("MEMBER_NOT_FOUND", "Member not found", status_code=404)

    # Owner's role is immutable
    if target_user_id == project.owner_id and new_role != ProjectRole.ADMIN:
        raise BusinessError(
            "FORBIDDEN", "Cannot change the project owner's role", status_code=403
        )

    # Last-admin guard: prevent demoting the only admin
    if member.role == ProjectRole.ADMIN and new_role == ProjectRole.MEMBER:
        admin_count = await project_members_repo.count_admins(db, project_id=project.id)
        if admin_count <= 1:
            raise BusinessError(
                "LAST_ADMIN", "Cannot demote the last admin", status_code=409
            )

    updated = await project_members_repo.update_role(db, member=member, role=new_role)
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=project.id,
        entity_type="member",
        entity_id=target_user_id,
        action="MEMBER_ROLE_CHANGED",
        metadata={"new_role": new_role.value},
    )
    await db.commit()
    return updated


async def remove_member(
    db: AsyncSession,
    *,
    project: Project,
    target_user_id: uuid.UUID,
    actor: User,
) -> None:
    member = await project_members_repo.get(
        db, project_id=project.id, user_id=target_user_id
    )
    if member is None:
        raise BusinessError("MEMBER_NOT_FOUND", "Member not found", status_code=404)

    if target_user_id == project.owner_id:
        raise BusinessError(
            "CANNOT_REMOVE_OWNER",
            "Transfer ownership before removing the owner",
            status_code=409,
        )

    await task_service.null_assignments_for_removed_member(
        db,
        project_id=project.id,
        user_id=target_user_id,
        actor_id=actor.id,
    )
    await activity_service.log(
        db,
        actor_id=actor.id,
        project_id=project.id,
        entity_type="member",
        entity_id=target_user_id,
        action="MEMBER_REMOVED",
        metadata={},
    )
    await project_members_repo.remove(db, member=member)
    await db.commit()
