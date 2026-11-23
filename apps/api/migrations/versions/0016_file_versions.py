"""File versions: series, version number, takeoff basis marker (FILE-002)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-24
"""

import sqlalchemy as sa
from alembic import op

from smart_engineer_api.db.base import NAMING_CONVENTION

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("project_files", naming_convention=NAMING_CONVENTION) as batch:
        batch.add_column(sa.Column("series_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("version_number", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("is_basis", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
        batch.add_column(sa.Column("restored_from_file_id", sa.Uuid(), nullable=True))
    # Every existing file becomes version 1 of its own series.
    op.execute("UPDATE project_files SET series_id = id, version_number = 1")
    with op.batch_alter_table("project_files", naming_convention=NAMING_CONVENTION) as batch:
        batch.alter_column("series_id", existing_type=sa.Uuid(), nullable=False)
        batch.alter_column("version_number", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            op.f("fk_project_files_restored_from_file_id_project_files"),
            "project_files",
            ["restored_from_file_id"],
            ["id"],
        )
        batch.create_check_constraint(
            op.f("ck_project_files_version_positive"), "version_number >= 1"
        )
        batch.create_unique_constraint(
            op.f("uq_project_files_series_version"), ["series_id", "version_number"]
        )
        batch.create_index("ix_project_files_series_id", ["series_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("project_files", naming_convention=NAMING_CONVENTION) as batch:
        batch.drop_index("ix_project_files_series_id")
        batch.drop_constraint(op.f("uq_project_files_series_version"), type_="unique")
        batch.drop_constraint(op.f("ck_project_files_version_positive"), type_="check")
        batch.drop_constraint(
            op.f("fk_project_files_restored_from_file_id_project_files"), type_="foreignkey"
        )
        batch.drop_column("restored_from_file_id")
        batch.drop_column("is_basis")
        batch.drop_column("version_number")
        batch.drop_column("series_id")
