from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=10000)
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_past(cls, v: date | None) -> date | None:
        if v is not None:
            from datetime import date as _date

            if v < _date.today():
                raise ValueError("due_date must be today or later")
        return v


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=10000)
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_past(cls, v: date | None) -> date | None:
        if v is not None:
            from datetime import date as _date

            if v < _date.today():
                raise ValueError("due_date must be today or later")
        return v


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskAssigneeInfo(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    creator_id: uuid.UUID
    assignee_id: uuid.UUID | None
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    size: int
