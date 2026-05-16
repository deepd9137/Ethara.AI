from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardStats,
    MyTasksResponse,
    RecentActivityResponse,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def stats(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardStats:
    return await dashboard_service.get_stats(db, user_id=user.id)


@router.get("/my-tasks", response_model=MyTasksResponse)
async def my_tasks(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MyTasksResponse:
    return await dashboard_service.get_my_tasks(db, user_id=user.id, limit=limit)


@router.get("/recent-activity", response_model=RecentActivityResponse)
async def recent_activity(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RecentActivityResponse:
    return await dashboard_service.get_recent_activity(db, user_id=user.id, limit=limit)
