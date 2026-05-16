"""add task model

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17 00:02:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a1"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'in_review', 'done')"
    )
    op.execute(
        "CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical')"
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assignee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "status",
            postgresql.ENUM(
                "todo",
                "in_progress",
                "in_review",
                "done",
                name="task_status",
                create_type=False,
            ),
            nullable=False,
            server_default="todo",
        ),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "critical",
                name="task_priority",
                create_type=False,
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "idx_tasks_project_alive",
        "tasks",
        ["project_id"],
        postgresql_where="deleted_at IS NULL",
    )
    op.create_index(
        "idx_tasks_assignee_open",
        "tasks",
        ["assignee_id"],
        postgresql_where="deleted_at IS NULL AND status <> 'done'",
    )
    op.create_index(
        "idx_tasks_due_date",
        "tasks",
        ["due_date"],
        postgresql_where="due_date IS NOT NULL AND status <> 'done'",
    )


def downgrade() -> None:
    op.drop_index("idx_tasks_due_date", table_name="tasks")
    op.drop_index("idx_tasks_assignee_open", table_name="tasks")
    op.drop_index("idx_tasks_project_alive", table_name="tasks")
    op.drop_table("tasks")
    op.execute("DROP TYPE task_priority")
    op.execute("DROP TYPE task_status")
