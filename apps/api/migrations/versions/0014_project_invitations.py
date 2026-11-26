"""Project-scoped invitations (FLOW-001)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-22
"""

import sqlalchemy as sa
from alembic import op

from smart_engineer_api.db.base import NAMING_CONVENTION

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

ROLES = "'owner', 'architect', 'structural_engineer', 'mep_engineer', 'quantity_surveyor'"


def upgrade() -> None:
    with op.batch_alter_table("invitations", naming_convention=NAMING_CONVENTION) as batch:
        batch.add_column(sa.Column("project_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("project_role", sa.String(length=30), nullable=True))
        batch.create_foreign_key(
            op.f("fk_invitations_project_id_projects"), "projects", ["project_id"], ["id"]
        )
        batch.create_check_constraint(
            op.f("ck_invitations_project_role_valid"), f"project_role IN ({ROLES})"
        )
        batch.create_check_constraint(
            op.f("ck_invitations_project_scope_complete"),
            "(project_id IS NULL AND project_role IS NULL)"
            " OR (project_id IS NOT NULL AND project_role IS NOT NULL)",
        )
        batch.create_index("ix_invitations_project_id", ["project_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("invitations", naming_convention=NAMING_CONVENTION) as batch:
        # MySQL refuses to drop an index that a foreign key still needs, so the foreign
        # key goes first (the order does not matter on PostgreSQL or SQLite).
        batch.drop_constraint(op.f("fk_invitations_project_id_projects"), type_="foreignkey")
        batch.drop_index("ix_invitations_project_id")
        batch.drop_constraint(op.f("ck_invitations_project_scope_complete"), type_="check")
        batch.drop_constraint(op.f("ck_invitations_project_role_valid"), type_="check")
        batch.drop_column("project_role")
        batch.drop_column("project_id")
