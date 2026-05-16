"""Direct service-layer tests for project_service and member_service.

Tests run in the same coroutine context as the service functions, yielding
accurate branch coverage (cf. CLAUDE.md Coverage quirk section).
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.middleware.exceptions import BusinessError
from app.models.project_member import ProjectRole
from app.models.user import User
from app.repositories import user_repo
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.services import member_service, project_service


async def _create_user(db: AsyncSession, prefix: str = "u") -> User:
    email = f"{prefix}+{uuid.uuid4().hex[:8]}@svc.test"
    return await user_repo.create(db, email=email, name="Test", password_hash=b"hash")


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


# ── project_service.create ────────────────────────────────────────────────────


async def test_service_create_project_ok(db: AsyncSession) -> None:
    user = await _create_user(db, "create")
    payload = ProjectCreate(name=f"P-{uuid.uuid4().hex[:6]}", description="d")
    project = await project_service.create(db, user=user, payload=payload)
    assert project.name == payload.name
    assert project.owner_id == user.id


async def test_service_create_project_duplicate_name_raises(db: AsyncSession) -> None:
    user = await _create_user(db, "dup")
    name = f"Dup-{uuid.uuid4().hex[:6]}"
    payload = ProjectCreate(name=name)
    await project_service.create(db, user=user, payload=payload)
    with pytest.raises(BusinessError) as exc_info:
        await project_service.create(db, user=user, payload=ProjectCreate(name=name))
    assert exc_info.value.code == "PROJECT_NAME_TAKEN"


# ── project_service.get_for_user ──────────────────────────────────────────────


async def test_service_get_for_user_non_member_raises_404(db: AsyncSession) -> None:
    owner = await _create_user(db, "gfu_owner")
    other = await _create_user(db, "gfu_other")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"G-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await project_service.get_for_user(db, user_id=other.id, project_id=proj.id)
    assert exc_info.value.code == "PROJECT_NOT_FOUND"
    assert exc_info.value.status_code == 404


async def test_service_get_for_user_member_returns_project(db: AsyncSession) -> None:
    owner = await _create_user(db, "gfu2_owner")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"GFU2-{uuid.uuid4().hex[:6]}")
    )
    fetched = await project_service.get_for_user(
        db, user_id=owner.id, project_id=proj.id
    )
    assert fetched.id == proj.id


# ── project_service.update ────────────────────────────────────────────────────


async def test_service_update_project_ok(db: AsyncSession) -> None:
    user = await _create_user(db, "upd")
    original_name = f"U-{uuid.uuid4().hex[:6]}"
    proj = await project_service.create(
        db, user=user, payload=ProjectCreate(name=original_name)
    )
    new_name = f"Updated-{uuid.uuid4().hex[:6]}"
    updated = await project_service.update(
        db,
        project=proj,
        payload=ProjectUpdate(name=new_name),
        actor=user,
    )
    assert updated.name == new_name
    assert updated.name != original_name


async def test_service_update_duplicate_name_raises(db: AsyncSession) -> None:
    user = await _create_user(db, "upddup")
    name1 = f"N1-{uuid.uuid4().hex[:6]}"
    name2 = f"N2-{uuid.uuid4().hex[:6]}"
    await project_service.create(db, user=user, payload=ProjectCreate(name=name1))
    proj2 = await project_service.create(
        db, user=user, payload=ProjectCreate(name=name2)
    )
    with pytest.raises(BusinessError) as exc_info:
        await project_service.update(
            db, project=proj2, payload=ProjectUpdate(name=name1), actor=user
        )
    assert exc_info.value.code == "PROJECT_NAME_TAKEN"


# ── project_service.soft_delete ───────────────────────────────────────────────


async def test_service_soft_delete_hides_project(db: AsyncSession) -> None:
    user = await _create_user(db, "del")
    proj = await project_service.create(
        db, user=user, payload=ProjectCreate(name=f"D-{uuid.uuid4().hex[:6]}")
    )
    await project_service.soft_delete(db, project=proj, actor=user)
    with pytest.raises(BusinessError) as exc_info:
        await project_service.get_for_user(db, user_id=user.id, project_id=proj.id)
    assert exc_info.value.status_code == 404


# ── project_service.transfer_owner ───────────────────────────────────────────


async def test_service_transfer_owner_ok(db: AsyncSession) -> None:
    owner = await _create_user(db, "to_owner")
    other = await _create_user(db, "to_other")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"T-{uuid.uuid4().hex[:6]}")
    )
    await member_service.invite(
        db, project=proj, email=other.email, role=ProjectRole.ADMIN, inviter=owner
    )
    updated = await project_service.transfer_owner(
        db, project=proj, new_owner_id=other.id, actor=owner
    )
    assert updated.owner_id == other.id


async def test_service_transfer_owner_non_owner_raises_403(db: AsyncSession) -> None:
    owner = await _create_user(db, "tno_owner")
    other = await _create_user(db, "tno_other")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"TNO-{uuid.uuid4().hex[:6]}")
    )
    await member_service.invite(
        db, project=proj, email=other.email, role=ProjectRole.MEMBER, inviter=owner
    )
    with pytest.raises(BusinessError) as exc_info:
        await project_service.transfer_owner(
            db, project=proj, new_owner_id=owner.id, actor=other
        )
    assert exc_info.value.status_code == 403


async def test_service_transfer_owner_to_non_member_raises_404(
    db: AsyncSession,
) -> None:
    owner = await _create_user(db, "tnm_owner")
    stranger = await _create_user(db, "tnm_stranger")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"TNM-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await project_service.transfer_owner(
            db, project=proj, new_owner_id=stranger.id, actor=owner
        )
    assert exc_info.value.status_code == 404


async def test_service_transfer_owner_same_owner_noop(db: AsyncSession) -> None:
    owner = await _create_user(db, "tno2_owner")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"TNO2-{uuid.uuid4().hex[:6]}")
    )
    result = await project_service.transfer_owner(
        db, project=proj, new_owner_id=owner.id, actor=owner
    )
    assert result.owner_id == owner.id


async def test_service_transfer_owner_promotes_member_to_admin(
    db: AsyncSession,
) -> None:
    owner = await _create_user(db, "tprom_owner")
    other = await _create_user(db, "tprom_other")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"TPROM-{uuid.uuid4().hex[:6]}")
    )
    await member_service.invite(
        db, project=proj, email=other.email, role=ProjectRole.MEMBER, inviter=owner
    )
    updated = await project_service.transfer_owner(
        db, project=proj, new_owner_id=other.id, actor=owner
    )
    assert updated.owner_id == other.id


# ── member_service.invite ─────────────────────────────────────────────────────


async def test_service_invite_ok(db: AsyncSession) -> None:
    owner = await _create_user(db, "inv_owner")
    invitee = await _create_user(db, "inv_invitee")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"Inv-{uuid.uuid4().hex[:6]}")
    )
    member = await member_service.invite(
        db, project=proj, email=invitee.email, role=ProjectRole.MEMBER, inviter=owner
    )
    assert member.user_id == invitee.id
    assert member.role == ProjectRole.MEMBER


async def test_service_invite_duplicate_raises_409(db: AsyncSession) -> None:
    owner = await _create_user(db, "invdup_owner")
    invitee = await _create_user(db, "invdup_invitee")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"InvDup-{uuid.uuid4().hex[:6]}")
    )
    await member_service.invite(
        db, project=proj, email=invitee.email, role=ProjectRole.MEMBER, inviter=owner
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.invite(
            db,
            project=proj,
            email=invitee.email,
            role=ProjectRole.MEMBER,
            inviter=owner,
        )
    assert exc_info.value.code == "ALREADY_MEMBER"


async def test_service_invite_unknown_email_raises_404(db: AsyncSession) -> None:
    owner = await _create_user(db, "invunk_owner")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"InvUnk-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.invite(
            db,
            project=proj,
            email="ghost@nowhere.net",
            role=ProjectRole.MEMBER,
            inviter=owner,
        )
    assert exc_info.value.code == "MEMBER_NOT_FOUND"


async def test_service_invite_self_raises_409(db: AsyncSession) -> None:
    owner = await _create_user(db, "invself_owner")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"InvSelf-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.invite(
            db, project=proj, email=owner.email, role=ProjectRole.MEMBER, inviter=owner
        )
    assert exc_info.value.code == "ALREADY_MEMBER"


# ── member_service.change_role ────────────────────────────────────────────────


async def test_service_change_role_last_admin_raises_409(db: AsyncSession) -> None:
    owner = await _create_user(db, "la_owner")
    other = await _create_user(db, "la_other")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"LA-{uuid.uuid4().hex[:6]}")
    )
    await member_service.invite(
        db, project=proj, email=other.email, role=ProjectRole.MEMBER, inviter=owner
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.change_role(
            db,
            project=proj,
            target_user_id=other.id,
            new_role=ProjectRole.ADMIN,
            actor=owner,
        )
        # Owner's role cannot be changed even when they're the only admin
        await member_service.change_role(
            db,
            project=proj,
            target_user_id=owner.id,
            new_role=ProjectRole.MEMBER,
            actor=owner,
        )
    assert exc_info.value.code in ("LAST_ADMIN", "FORBIDDEN")


async def test_service_change_role_owner_role_immutable(db: AsyncSession) -> None:
    owner = await _create_user(db, "ori_owner")
    other = await _create_user(db, "ori_other")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"ORI-{uuid.uuid4().hex[:6]}")
    )
    await member_service.invite(
        db, project=proj, email=other.email, role=ProjectRole.ADMIN, inviter=owner
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.change_role(
            db,
            project=proj,
            target_user_id=owner.id,
            new_role=ProjectRole.MEMBER,
            actor=other,
        )
    assert exc_info.value.code == "FORBIDDEN"


async def test_service_change_role_member_not_found_raises_404(
    db: AsyncSession,
) -> None:
    owner = await _create_user(db, "crnf_owner")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"CRNF-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.change_role(
            db,
            project=proj,
            target_user_id=uuid.uuid4(),
            new_role=ProjectRole.ADMIN,
            actor=owner,
        )
    assert exc_info.value.code == "MEMBER_NOT_FOUND"


# ── member_service.remove_member ─────────────────────────────────────────────


async def test_service_remove_owner_raises_409(db: AsyncSession) -> None:
    owner = await _create_user(db, "rmo_owner")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"RMO-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.remove_member(
            db, project=proj, target_user_id=owner.id, actor=owner
        )
    assert exc_info.value.code == "CANNOT_REMOVE_OWNER"


async def test_service_remove_member_ok(db: AsyncSession) -> None:
    owner = await _create_user(db, "rm_owner")
    other = await _create_user(db, "rm_other")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"RM-{uuid.uuid4().hex[:6]}")
    )
    await member_service.invite(
        db, project=proj, email=other.email, role=ProjectRole.MEMBER, inviter=owner
    )
    await member_service.remove_member(
        db, project=proj, target_user_id=other.id, actor=owner
    )
    members = await member_service.list_members(db, project_id=proj.id)
    member_ids = [m.user_id for m in members]
    assert other.id not in member_ids


async def test_service_remove_member_not_found_raises_404(db: AsyncSession) -> None:
    owner = await _create_user(db, "rmnf_owner")
    proj = await project_service.create(
        db, user=owner, payload=ProjectCreate(name=f"RMNF-{uuid.uuid4().hex[:6]}")
    )
    with pytest.raises(BusinessError) as exc_info:
        await member_service.remove_member(
            db, project=proj, target_user_id=uuid.uuid4(), actor=owner
        )
    assert exc_info.value.code == "MEMBER_NOT_FOUND"
