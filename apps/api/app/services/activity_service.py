import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.repositories import activity_repo


async def log(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    metadata: dict[str, Any] | None = None,
) -> ActivityLog:
    return await activity_repo.log(
        db,
        actor_id=actor_id,
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        metadata=metadata,
    )
