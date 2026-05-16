import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession, *, email: str, name: str, password_hash: bytes
) -> User:
    user = User(email=email.lower(), name=name, password_hash=password_hash)
    db.add(user)
    await db.flush()
    return user


async def increment_failed_login(db: AsyncSession, user: User) -> None:
    user.failed_login_count += 1
    await db.flush()


async def set_locked_until(
    db: AsyncSession, user: User, locked_until: datetime | None
) -> None:
    user.locked_until = locked_until
    user.failed_login_count = 0
    await db.flush()


async def reset_failed_login(db: AsyncSession, user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    await db.flush()


async def update_password(db: AsyncSession, user: User, password_hash: bytes) -> None:
    user.password_hash = password_hash
    await db.flush()
