import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import (
    ActivityItem,
    DashboardStats,
    MyTask,
    MyTaskProject,
    MyTasksResponse,
    RecentActivityResponse,
)


async def get_stats(db: AsyncSession, *, user_id: uuid.UUID) -> DashboardStats:
    sql = text("""
        SELECT
          COUNT(*) FILTER (WHERE t.status <> 'done')                                     AS open,
          COUNT(*) FILTER (WHERE t.status <> 'done' AND t.due_date < CURRENT_DATE)       AS overdue,
          COUNT(*) FILTER (WHERE t.status <> 'done' AND t.due_date <= CURRENT_DATE + 7)  AS due_week
        FROM tasks t
        JOIN project_members m ON m.project_id = t.project_id
        WHERE m.user_id = :uid AND t.deleted_at IS NULL
    """)
    row = (await db.execute(sql, {"uid": str(user_id)})).one()
    return DashboardStats(
        open=int(row.open),
        overdue=int(row.overdue),
        due_this_week=int(row.due_week),
    )


async def get_my_tasks(
    db: AsyncSession, *, user_id: uuid.UUID, limit: int = 20
) -> MyTasksResponse:
    limit = min(limit, 100)

    count_sql = text("""
        SELECT COUNT(*)
        FROM tasks t
        JOIN projects p ON p.id = t.project_id
        WHERE t.assignee_id = :uid
          AND t.status <> 'done'
          AND t.deleted_at IS NULL
          AND p.deleted_at IS NULL
    """)
    total: int = (await db.execute(count_sql, {"uid": str(user_id)})).scalar_one()

    items_sql = text("""
        SELECT
          t.id         AS task_id,
          t.title,
          t.status,
          t.priority,
          t.due_date,
          p.id         AS project_id,
          p.name       AS project_name
        FROM tasks t
        JOIN projects p ON p.id = t.project_id
        WHERE t.assignee_id = :uid
          AND t.status <> 'done'
          AND t.deleted_at IS NULL
          AND p.deleted_at IS NULL
        ORDER BY
          (t.due_date IS NULL) ASC,
          t.due_date ASC,
          CASE t.priority
            WHEN 'critical' THEN 4
            WHEN 'high'     THEN 3
            WHEN 'medium'   THEN 2
            WHEN 'low'      THEN 1
          END DESC
        LIMIT :lim
    """)
    rows = (await db.execute(items_sql, {"uid": str(user_id), "lim": limit})).all()

    items = [
        MyTask(
            id=row.task_id,
            project=MyTaskProject(id=row.project_id, name=row.project_name),
            title=row.title,
            status=row.status,
            priority=row.priority,
            due_date=row.due_date,
        )
        for row in rows
    ]
    return MyTasksResponse(items=items, total=total)


async def get_recent_activity(
    db: AsyncSession, *, user_id: uuid.UUID, limit: int = 20
) -> RecentActivityResponse:
    limit = min(limit, 100)

    count_sql = text("""
        SELECT COUNT(*)
        FROM activity_logs al
        JOIN project_members m ON m.project_id = al.project_id AND m.user_id = :uid
        WHERE al.project_id IS NOT NULL
    """)
    total: int = (await db.execute(count_sql, {"uid": str(user_id)})).scalar_one()

    items_sql = text("""
        SELECT
          al.id          AS log_id,
          al.entity_type,
          al.entity_id,
          al.action,
          al.project_id,
          al.created_at,
          u.name         AS actor_name,
          p.name         AS project_name
        FROM activity_logs al
        JOIN project_members m ON m.project_id = al.project_id AND m.user_id = :uid
        LEFT JOIN users u ON u.id = al.actor_id
        LEFT JOIN projects p ON p.id = al.project_id
        WHERE al.project_id IS NOT NULL
        ORDER BY al.created_at DESC
        LIMIT :lim
    """)
    rows = (await db.execute(items_sql, {"uid": str(user_id), "lim": limit})).all()

    items = [
        ActivityItem(
            id=row.log_id,
            actor_name=row.actor_name,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            project_id=row.project_id,
            project_name=row.project_name,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return RecentActivityResponse(items=items, total=total)
