"""Zoning / building-control records

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zoning_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=30), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "field_key IN ('land_use', 'coverage', 'density', 'floors_height', 'setbacks', "
            "'parking_access', 'daylight_openings', 'circulation', 'local_constraints')",
            name=op.f("ck_zoning_records_field_key_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_zoning_records_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name=op.f("fk_zoning_records_updated_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zoning_records")),
        sa.UniqueConstraint("project_id", "field_key", name=op.f("uq_zoning_records_project_id")),
    )


def downgrade() -> None:
    op.drop_table("zoning_records")
