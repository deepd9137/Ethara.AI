import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password, verify_password
from app.auth.tokens import encode_access
from app.middleware.exceptions import BusinessError
from app.models.user import User
from app.repositories import refresh_token_repo, user_repo

_MAX_FAILED = 10
_LOCKOUT_SECONDS = 15 * 60


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def signup(
    db: AsyncSession, *, email: str, name: str, password: str
) -> tuple[User, str, str]:
    if await user_repo.get_by_email(db, email):
        raise BusinessError("EMAIL_TAKEN", "Email already registered", status_code=409)

    user = await user_repo.create(
        db,
        email=email,
        name=name,
        password_hash=hash_password(password),
    )
    access, refresh = await _issue_tokens(db, user.id)
    await db.commit()
    return user, access, refresh


async def login(
    db: AsyncSession, *, email: str, password: str
) -> tuple[User, str, str]:
    user = await user_repo.get_by_email(db, email)

    # Always hash even on miss to prevent timing oracle
    dummy_hash = b"$2b$12$" + b"x" * 53
    candidate_hash = user.password_hash if user else dummy_hash

    if user and user.locked_until and user.locked_until > _utc_now():
        retry_after = int((user.locked_until - _utc_now()).total_seconds())
        raise BusinessError(
            "ACCOUNT_LOCKED",
            "Account temporarily locked",
            status_code=423,
            details={"retry_after": retry_after},
        )

    password_ok = verify_password(password, candidate_hash) if user else False

    if not user or not password_ok:
        if user:
            await user_repo.increment_failed_login(db, user)
            if user.failed_login_count >= _MAX_FAILED:
                from datetime import timedelta

                locked_until = _utc_now() + timedelta(seconds=_LOCKOUT_SECONDS)
                await user_repo.set_locked_until(db, user, locked_until)
        await db.commit()
        raise BusinessError(
            "INVALID_CREDENTIALS", "Invalid email or password", status_code=401
        )

    await user_repo.reset_failed_login(db, user)
    access, refresh = await _issue_tokens(db, user.id)
    await db.commit()
    return user, access, refresh


async def rotate_refresh(db: AsyncSession, raw_token: str) -> tuple[str, str]:
    record = await refresh_token_repo.get_by_hash(db, raw_token)

    if record is None:
        raise BusinessError("REFRESH_EXPIRED", "Refresh token expired", status_code=401)

    if record.expires_at < _utc_now():
        await refresh_token_repo.revoke_family(db, record.family_id)
        await db.commit()
        raise BusinessError("REFRESH_EXPIRED", "Refresh token expired", status_code=401)

    if record.used_at is not None:
        # Reuse detected — revoke entire family
        await refresh_token_repo.revoke_family(db, record.family_id)
        await db.commit()
        raise BusinessError("REFRESH_REUSED", "Token reuse detected", status_code=401)

    await refresh_token_repo.mark_used(db, record)
    new_raw = await refresh_token_repo.issue(
        db, user_id=record.user_id, family_id=record.family_id
    )
    access = encode_access(record.user_id)
    await db.commit()
    return access, new_raw


async def logout(db: AsyncSession, raw_token: str) -> None:
    record = await refresh_token_repo.get_by_hash(db, raw_token)
    if record:
        await refresh_token_repo.revoke_family(db, record.family_id)
        await db.commit()


async def change_password(
    db: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise BusinessError(
            "BAD_CURRENT", "Current password is incorrect", status_code=401
        )

    await user_repo.update_password(db, user, hash_password(new_password))
    await refresh_token_repo.revoke_all_for_user(db, user.id)
    await db.commit()


async def _issue_tokens(db: AsyncSession, user_id: uuid.UUID) -> tuple[str, str]:
    family_id = uuid.uuid4()
    raw_refresh = await refresh_token_repo.issue(
        db, user_id=user_id, family_id=family_id
    )
    access = encode_access(user_id)
    return access, raw_refresh
