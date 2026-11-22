"""Project file attachment metadata

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("original_name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=True),
        sa.Column("ownership", sa.String(length=200), nullable=True),
        sa.Column("detected_type", sa.String(length=10), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column("scan_status", sa.String(length=20), nullable=False),
        sa.Column("scan_detail", sa.String(length=200), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('survey', 'deed', 'zoning_letter', 'geotechnical_report', "
            "'site_photo', 'reference_image', 'other')",
            name=op.f("ck_project_files_kind_valid"),
        ),
        sa.CheckConstraint(
            "detected_type IN ('pdf', 'png', 'jpeg', 'webp')",
            name=op.f("ck_project_files_detected_type_valid"),
        ),
        sa.CheckConstraint(
            "scan_status IN ('pending', 'clean', 'quarantined')",
            name=op.f("ck_project_files_scan_status_valid"),
        ),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_project_files_size_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_project_files_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_project_files_uploaded_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by_user_id"],
            ["users.id"],
            name=op.f("fk_project_files_deleted_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_files")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_project_files_storage_key")),
    )
    op.create_index("ix_project_files_project_id", "project_files", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_project_files_project_id", table_name="project_files")
    op.drop_table("project_files")
