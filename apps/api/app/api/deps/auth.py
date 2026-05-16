import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import decode_access
from app.db.session import get_db
from app.middleware.exceptions import BusinessError
from app.models.user import User
from app.repositories import user_repo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        claims = decode_access(token)
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, KeyError) as exc:
        raise BusinessError(
            "INVALID_TOKEN", "Could not validate credentials", status_code=401
        ) from exc

    user = await user_repo.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise BusinessError(
            "INVALID_TOKEN", "Could not validate credentials", status_code=401
        )
    return user
