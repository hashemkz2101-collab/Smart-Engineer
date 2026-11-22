"""Platform administrator audit events

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_events",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_project_id", sa.Uuid(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_admin_audit_events_actor_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name=op.f("fk_admin_audit_events_target_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["target_project_id"],
            ["projects.id"],
            name=op.f("fk_admin_audit_events_target_project_id_projects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_audit_events")),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_events")
