import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import generate_refresh_token, hash_token, refresh_expires_at
from app.models.refresh_token import RefreshToken


async def issue(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
) -> str:
    raw = generate_refresh_token()
    record = RefreshToken(
        user_id=user_id,
        family_id=family_id,
        token_hash=hash_token(raw),
        expires_at=refresh_expires_at(),
    )
    db.add(record)
    await db.flush()
    return raw


async def get_by_hash(db: AsyncSession, raw: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(raw),
            RefreshToken.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def mark_used(db: AsyncSession, record: RefreshToken) -> None:
    record.used_at = datetime.now(UTC)
    await db.flush()


async def revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
