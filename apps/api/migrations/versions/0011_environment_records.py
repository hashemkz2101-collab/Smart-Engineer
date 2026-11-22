"""Environmental condition records

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "environment_records",
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
            "field_key IN ('climate', 'solar', 'wind', 'rainfall', 'design_temperature', "
            "'hazards', 'seismicity', 'water', 'electricity', 'gas', 'sewer', 'telecom', "
            "'energy')",
            name=op.f("ck_environment_records_field_key_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_environment_records_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name=op.f("fk_environment_records_updated_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_environment_records")),
        sa.UniqueConstraint(
            "project_id", "field_key", name=op.f("uq_environment_records_project_id")
        ),
    )


def downgrade() -> None:
    op.drop_table("environment_records")
