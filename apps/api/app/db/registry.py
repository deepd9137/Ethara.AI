# Import all ORM models so Alembic autogenerate detects them.
# This module must not be imported by any model — only by alembic/env.py.
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.user import User  # noqa: F401
