"""add_project_models

Revision ID: a1b2c3d4e5f6
Revises: 0223b249cdd5
Create Date: 2026-05-17 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "0223b249cdd5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create project_role enum type first
    op.execute("CREATE TYPE project_role AS ENUM ('admin', 'member')")

    # projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Partial index: live projects per owner
    op.create_index(
        "idx_projects_owner_alive",
        "projects",
        ["owner_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    # Unique constraint: one project name per owner among non-deleted projects
    # NULLS NOT DISTINCT treats NULL deleted_at as equal, preventing duplicate
    # names even when deleted_at is NULL.
    op.execute("""
        ALTER TABLE projects
        ADD CONSTRAINT projects_name_per_owner_uq
        UNIQUE NULLS NOT DISTINCT (owner_id, name, deleted_at)
        """)

    # project_members table
    op.create_table(
        "project_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "member", name="project_role", create_type=False),
            nullable=False,
        ),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "user_id", name="project_members_unique_pair"
        ),
    )
    op.create_index("idx_pm_user", "project_members", ["user_id"])
    op.create_index("idx_pm_project", "project_members", ["project_id"])

    # activity_logs table
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_activity_project_created",
        "activity_logs",
        ["project_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index("idx_activity_actor", "activity_logs", ["actor_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_activity_actor", table_name="activity_logs")
    op.drop_index("idx_activity_project_created", table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_index("idx_pm_project", table_name="project_members")
    op.drop_index("idx_pm_user", table_name="project_members")
    op.drop_table("project_members")

    op.drop_index("idx_projects_owner_alive", table_name="projects")
    op.execute(
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_name_per_owner_uq"
    )
    op.drop_table("projects")

    op.execute("DROP TYPE project_role")
