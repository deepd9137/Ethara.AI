import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.project_member import ProjectRole


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: ProjectRole = ProjectRole.MEMBER


class ChangeMemberRoleRequest(BaseModel):
    role: ProjectRole


class MemberUserInfo(BaseModel):
    id: uuid.UUID
    email: str
    name: str

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: ProjectRole
    invited_by: uuid.UUID | None
    created_at: datetime
    user: MemberUserInfo

    model_config = {"from_attributes": True}


class MemberListResponse(BaseModel):
    items: list[MemberResponse]
    total: int
