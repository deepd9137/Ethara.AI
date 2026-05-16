import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.rbac import require_project_admin, require_project_member
from app.db.session import get_db
from app.middleware.exceptions import BusinessError
from app.models.project_member import ProjectMember
from app.models.user import User
from app.repositories import projects_repo
from app.schemas.projects import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    TransferOwnerRequest,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await project_service.create(db, user=current_user, payload=body)
    return ProjectResponse.model_validate(project)


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    sort: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    items, total = await project_service.list_for_user(
        db, user=current_user, page=page, size=size, q=q, sort=sort
    )
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await project_service.get_for_user(
        db, user_id=current_user.id, project_id=project_id
    )
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member: ProjectMember = Depends(require_project_admin),
) -> ProjectResponse:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    updated = await project_service.update(
        db, project=project, payload=body, actor=current_user
    )
    return ProjectResponse.model_validate(updated)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member: ProjectMember = Depends(require_project_admin),
) -> None:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    await project_service.soft_delete(db, project=project, actor=current_user)


@router.post("/{project_id}/transfer-owner")
async def transfer_owner(
    project_id: uuid.UUID,
    body: TransferOwnerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member: ProjectMember = Depends(require_project_member),
) -> ProjectResponse:
    project = await projects_repo.get_by_id(db, project_id)
    if project is None:
        raise BusinessError("PROJECT_NOT_FOUND", "Project not found", status_code=404)
    updated = await project_service.transfer_owner(
        db, project=project, new_owner_id=body.user_id, actor=current_user
    )
    return ProjectResponse.model_validate(updated)
