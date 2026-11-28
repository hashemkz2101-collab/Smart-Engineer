"""Saved design versions and comments (ARCH-006)

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "design_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("number >= 1", name=op.f("ck_design_versions_number_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_design_versions_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_design_versions_created_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_design_versions")),
        sa.UniqueConstraint("project_id", "number", name=op.f("uq_design_versions_project_id")),
    )
    op.create_table(
        "design_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("element_id", sa.String(length=20), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_design_comments_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["design_versions.id"],
            name=op.f("fk_design_comments_version_id_design_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["users.id"], name=op.f("fk_design_comments_author_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_design_comments")),
    )


def downgrade() -> None:
    op.drop_table("design_comments")
    op.drop_table("design_versions")
