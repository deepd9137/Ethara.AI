import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog


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
    entry = ActivityLog(
        actor_id=actor_id,
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        meta=metadata or {},
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_by_project(
    db: AsyncSession, *, project_id: uuid.UUID, limit: int = 50
) -> list[ActivityLog]:
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.project_id == project_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
