import bcrypt

from app.core.config import settings


def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(
        plain.encode()[:72], bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    )


def verify_password(plain: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed)
    except Exception:
        return False
