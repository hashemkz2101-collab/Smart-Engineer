"""Allow CAD, BIM, Office and CSV uploads (FILE-001, DEC-023)

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-24
"""

from alembic import op

from smart_engineer_api.db.base import NAMING_CONVENTION

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

OLD = ("pdf", "png", "jpeg", "webp")
NEW = OLD + ("dxf", "dwg", "ifc", "xlsx", "xls", "csv", "docx", "doc")


def _in(values: tuple[str, ...]) -> str:
    return "detected_type IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def _swap(values: tuple[str, ...]) -> None:
    with op.batch_alter_table("project_files", naming_convention=NAMING_CONVENTION) as batch:
        batch.drop_constraint("ck_project_files_detected_type_valid", type_="check")
        batch.create_check_constraint(
            op.f("ck_project_files_detected_type_valid"), _in(values)
        )


def upgrade() -> None:
    _swap(NEW)


def downgrade() -> None:
    op.execute("DELETE FROM project_files WHERE detected_type NOT IN ('pdf','png','jpeg','webp')")
    _swap(OLD)
