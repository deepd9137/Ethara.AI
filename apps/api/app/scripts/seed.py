"""First-deploy seed: idempotent demo user + sample project/tasks.

Usage (local):  uv run python -m app.scripts.seed
Usage (Railway): railway run --service api uv run python -m app.scripts.seed

Safe to run repeatedly — every insert is guarded by an existence check.
Credentials are intentionally weak; this is a demo account for the assessment
reviewer, never a real user.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.auth.password import hash_password
from app.db.session import AsyncSessionLocal
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@ethara.example"
DEMO_PASSWORD = "DemoPass123!"  # noqa: S105 — demo creds, public by design
DEMO_NAME = "Demo User"
DEMO_PROJECT_NAME = "Welcome to Ethara"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == DEMO_EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                id=uuid.uuid4(),
                email=DEMO_EMAIL,
                name=DEMO_NAME,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
            )
            db.add(user)
            await db.flush()
            logger.info("created demo user %s", DEMO_EMAIL)
        else:
            logger.info("demo user already exists, skipping")

        project = (
            await db.execute(
                select(Project).where(
                    Project.owner_id == user.id,
                    Project.name == DEMO_PROJECT_NAME,
                    Project.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if project is None:
            project = Project(
                id=uuid.uuid4(),
                owner_id=user.id,
                name=DEMO_PROJECT_NAME,
                description="Sample project seeded on first deploy.",
            )
            db.add(project)
            await db.flush()
            db.add(
                ProjectMember(
                    project_id=project.id,
                    user_id=user.id,
                    role=ProjectRole.ADMIN,
                    invited_by=user.id,
                )
            )
            await db.flush()
            logger.info("created demo project %s", project.id)
        else:
            logger.info("demo project already exists, skipping")

        existing_titles = {
            row[0]
            for row in (
                await db.execute(
                    select(Task.title).where(
                        Task.project_id == project.id, Task.deleted_at.is_(None)
                    )
                )
            ).all()
        }
        samples = [
            (
                "Read the README",
                "Quick tour of the codebase and the live URL.",
                TaskStatus.DONE,
                TaskPriority.LOW,
                None,
            ),
            (
                "Try the kanban board",
                "Drag a card across columns to see optimistic updates in action.",
                TaskStatus.IN_PROGRESS,
                TaskPriority.MEDIUM,
                date.today() + timedelta(days=3),
            ),
            (
                "Invite a teammate",
                "Add a project member from the Members tab — RBAC kicks in immediately.",
                TaskStatus.TODO,
                TaskPriority.HIGH,
                date.today() + timedelta(days=7),
            ),
        ]
        for title, description, status, priority, due in samples:
            if title in existing_titles:
                continue
            db.add(
                Task(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    creator_id=user.id,
                    assignee_id=user.id,
                    title=title,
                    description=description,
                    status=status,
                    priority=priority,
                    due_date=due,
                    completed_at=(
                        datetime.now(UTC) if status == TaskStatus.DONE else None
                    ),
                )
            )
        await db.commit()
        logger.info("seed complete")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    asyncio.run(seed())


if __name__ == "__main__":
    main()
