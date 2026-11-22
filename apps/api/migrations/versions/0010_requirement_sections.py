"""Client requirement sections

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("section_key", sa.String(length=30), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("complete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "section_key IN ('program', 'preferences', 'references')",
            name=op.f("ck_requirement_sections_section_key_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_requirement_sections_project_id_projects"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name=op.f("fk_requirement_sections_updated_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requirement_sections")),
        sa.UniqueConstraint(
            "project_id", "section_key", name=op.f("uq_requirement_sections_project_id")
        ),
    )


def downgrade() -> None:
    op.drop_table("requirement_sections")
