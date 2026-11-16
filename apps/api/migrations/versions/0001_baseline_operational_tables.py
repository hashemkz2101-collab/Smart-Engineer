"""Baseline operational tables: feature_flags and background_jobs

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("key", name=op.f("pk_feature_flags")),
    )
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_background_jobs_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_background_jobs")),
    )
    op.create_index(
        op.f("ix_background_jobs_status"), "background_jobs", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_background_jobs_status"), table_name="background_jobs")
    op.drop_table("background_jobs")
    op.drop_table("feature_flags")
