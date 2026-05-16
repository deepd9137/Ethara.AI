import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def encode_access(user_id: uuid.UUID) -> str:
    now = _utc_now()
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + settings.JWT_ACCESS_TTL_SECONDS,
        "jti": str(uuid.uuid4()),
    }
    return str(jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM))


def decode_access(token: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[ALGORITHM]
        )
        return result
    except JWTError as exc:
        raise ValueError("invalid_access_token") from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


def refresh_expires_at() -> datetime:
    return _utc_now() + timedelta(seconds=settings.JWT_REFRESH_TTL_SECONDS)
