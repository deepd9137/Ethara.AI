import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.task import TaskPriority, TaskStatus


class DashboardStats(BaseModel):
    open: int
    overdue: int
    due_this_week: int


class MyTaskProject(BaseModel):
    id: uuid.UUID
    name: str


class MyTask(BaseModel):
    id: uuid.UUID
    project: MyTaskProject
    title: str
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None


class MyTasksResponse(BaseModel):
    items: list[MyTask]
    total: int


class ActivityItem(BaseModel):
    id: uuid.UUID
    actor_name: str | None
    entity_type: str
    entity_id: uuid.UUID
    action: str
    project_id: uuid.UUID | None
    project_name: str | None
    created_at: datetime


class RecentActivityResponse(BaseModel):
    items: list[ActivityItem]
    total: int
