# Import all ORM models so Alembic autogenerate detects them.
# This module must not be imported by any model — only by alembic/env.py.
from app.models.activity_log import ActivityLog  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_member import ProjectMember  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
