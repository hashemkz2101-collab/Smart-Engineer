"""Design history for undo/redo (ARCH-004)

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "design_models",
        sa.Column("head_seq", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_table(
        "design_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("seq >= 1", name=op.f("ck_design_history_seq_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_design_history_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_design_history_actor_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_design_history")),
        sa.UniqueConstraint("project_id", "seq", name=op.f("uq_design_history_project_id")),
    )


def downgrade() -> None:
    op.drop_table("design_history")
    op.drop_column("design_models", "head_seq")
