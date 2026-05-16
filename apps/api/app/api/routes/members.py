import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps.auth import get_current_user
from app.api.deps.rbac import require_project_admin, require_project_member
from app.db.session import get_db
from app.middleware.exceptions import BusinessError
from app.models.project_member import ProjectMember
from app.models.user import User
from app.repositories import projects_repo
from app.schemas.members import (
    ChangeMemberRoleRequest,
    InviteMemberRequest,
    MemberListResponse,
    MemberResponse,
)
from app.services import member_service

router = APIRouter(prefix="/projects", tags=["members"])


async def _load_member_with_user(
    db: AsyncSession, member_id: uuid.UUID
) -> ProjectMember:
    result = await db.execute(
        select(ProjectMember)
        .where(ProjectMember.id == member_id)
        .options(selectinload(ProjectMember.user))
    )
    return result.scalar_one()


@router.post("/{project_id}/members", status_code=201)
async def invite_member(
    project_id: uuid.UUID,
    body: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member: ProjectMember = Depends(require_project_admin),
) -> MemberResponse:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    member = await member_service.invite(
        db, project=project, email=body.email, role=body.role, inviter=current_user
    )
    loaded = await _load_member_with_user(db, member.id)
    return MemberResponse.model_validate(loaded)


@router.get("/{project_id}/members")
async def list_members(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _member: ProjectMember = Depends(require_project_member),
) -> MemberListResponse:
    members = await member_service.list_members(db, project_id=project_id)
    return MemberListResponse(
        items=[MemberResponse.model_validate(m) for m in members],
        total=len(members),
    )


@router.patch("/{project_id}/members/{user_id}")
async def change_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    body: ChangeMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member: ProjectMember = Depends(require_project_admin),
) -> MemberResponse:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    updated = await member_service.change_role(
        db,
        project=project,
        target_user_id=user_id,
        new_role=body.role,
        actor=current_user,
    )
    loaded = await _load_member_with_user(db, updated.id)
    return MemberResponse.model_validate(loaded)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member: ProjectMember = Depends(require_project_admin),
) -> None:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    await member_service.remove_member(
        db, project=project, target_user_id=user_id, actor=current_user
    )
