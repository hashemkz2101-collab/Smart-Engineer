"""Identity, organization, and project tables (Phase 1, P1-01).

Policies encoded here (see docs/PHASE_1_PLAN.md and DEC-016/017/022):

* Emails are stored lowercase and unique.
* An organization is the tenant. A project belongs to exactly one organization.
* Projects are archived, never hard-deleted: ``archived_at`` is set together
  with ``status = 'archived'`` and foreign keys do not cascade deletes.
* Project-scoped roles live on ``project_members``; ``is_system_admin`` is a
  platform flag on users.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..roles import (
    AUTH_TOKEN_PURPOSES,
    ENV_FIELDS,
    FILE_KINDS,
    FILE_SCAN_STATUSES,
    FILE_TYPES,
    INTAKE_STEPS,
    INVITABLE_ORG_ROLES,
    ORG_ROLES,
    PROJECT_ROLES,
    PROJECT_STATUSES,
    PROJECT_TYPES,
    REQUIREMENT_SECTIONS,
    SITE_SECTIONS,
    ZONING_FIELDS,
    sql_in,
)
from .base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    is_system_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        CheckConstraint(sql_in("org_role", ORG_ROLES), name="org_role_valid"),
        Index("ix_memberships_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    org_role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(sql_in("project_type", PROJECT_TYPES), name="project_type_valid"),
        CheckConstraint(sql_in("status", PROJECT_STATUSES), name="status_valid"),
        CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) "
            "OR (status = 'active' AND archived_at IS NULL)",
            name="archive_consistent",
        ),
        Index("ix_projects_organization_id_status", "organization_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    project_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default=text("'active'")
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id"),
        CheckConstraint(sql_in("role", PROJECT_ROLES), name="role_valid"),
        Index("ix_project_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    added_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuthSession(Base):
    """A login session. Only the SHA-256 digest of the cookie token is stored."""

    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Synchronizer token for CSRF; only meaningful together with the session cookie.
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuthToken(Base):
    """Single-use token for password reset or email verification (hashed)."""

    __tablename__ = "auth_tokens"
    __table_args__ = (
        CheckConstraint(sql_in("purpose", AUTH_TOKEN_PURPOSES), name="purpose_valid"),
        Index("ix_auth_tokens_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LoginFailure(Base):
    """One failed login attempt, kept only to enforce the lockout window.

    Stores the attempted (lowercased) email and a time. No IP address is stored
    (DEC-026 privacy default).
    """

    __tablename__ = "login_failures"
    __table_args__ = (Index("ix_login_failures_email_created_at", "email", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Invitation(Base):
    """Invitation to join an organization. Only the token's SHA-256 is stored."""

    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint(sql_in("org_role", INVITABLE_ORG_ROLES), name="org_role_valid"),
        CheckConstraint(sql_in("project_role", PROJECT_ROLES), name="project_role_valid"),
        CheckConstraint(
            "(project_id IS NULL AND project_role IS NULL)"
            " OR (project_id IS NOT NULL AND project_role IS NOT NULL)",
            name="project_scope_complete",
        ),
        Index("ix_invitations_organization_id", "organization_id"),
        Index("ix_invitations_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    org_role: Mapped[str] = mapped_column(String(20), nullable=False)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    # Set for a project invitation (FLOW-001): accepting it also grants this project role.
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    project_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ActivityEvent(Base):
    """Append-only, ordered project activity record (PRJ-002).

    The integer primary key increases with insertion, so ordering never depends
    on clock resolution.
    """

    __tablename__ = "activity_events"
    __table_args__ = (Index("ix_activity_events_project_id", "project_id", "id"),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IntakeStep(Base):
    """One saved step of a project's intake form (INP-001/002).

    ``data`` holds only the non-empty, validated fields. A step can be saved
    incomplete; ``complete`` is derived from the required fields on every save.
    ``version`` supports optimistic locking so two devices cannot silently
    overwrite each other.
    """

    __tablename__ = "intake_steps"
    __table_args__ = (
        UniqueConstraint("project_id", "step_key"),
        CheckConstraint(sql_in("step_key", INTAKE_STEPS), name="step_key_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    step_key: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SiteSection(Base):
    """One saved section of a project's site / land data (SITE-001/002).

    Same versioned-document pattern as ``IntakeStep``. ``data`` holds only values
    the user supplied: omitted optional values are never defaulted, so a missing
    soil value stays missing. Explicitly empty lists are kept (they mean "none").
    """

    __tablename__ = "site_sections"
    __table_args__ = (
        UniqueConstraint("project_id", "section_key"),
        CheckConstraint(sql_in("section_key", SITE_SECTIONS), name="section_key_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    section_key: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ZoningRecord(Base):
    """One zoning / building-control category with its source (RULE-DATA-001).

    ``data`` holds the user-entered values plus the source reference. Whether a
    record is unknown, needs inquiry or is verified is derived on read; nothing
    is ever stored as law without a source, and unverified values stay flagged.
    """

    __tablename__ = "zoning_records"
    __table_args__ = (
        UniqueConstraint("project_id", "field_key"),
        CheckConstraint(sql_in("field_key", ZONING_FIELDS), name="field_key_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    field_key: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RequirementSection(Base):
    """One saved section of the client's requirements (REQ-001/002/003).

    Same versioned-document pattern as ``SiteSection``: only supplied values are
    stored, omitted values are never defaulted, and an explicit empty list means
    "none".
    """

    __tablename__ = "requirement_sections"
    __table_args__ = (
        UniqueConstraint("project_id", "section_key"),
        CheckConstraint(sql_in("section_key", REQUIREMENT_SECTIONS), name="section_key_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    section_key: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EnvironmentRecord(Base):
    """One environmental / technical-condition category with its source (ENV-001).

    ``data`` holds the user-entered values plus source, location and date. Status is
    derived on read; nothing is stored as fact without a source.
    """

    __tablename__ = "environment_records"
    __table_args__ = (
        UniqueConstraint("project_id", "field_key"),
        CheckConstraint(sql_in("field_key", ENV_FIELDS), name="field_key_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    field_key: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectFile(Base):
    """Metadata of one uploaded project file (FILE-001, SEC-002).

    The bytes live in private storage under ``storage_key`` (never a public path).
    ``deleted_at`` marks a removed file whose bytes are gone but whose metadata is
    kept for the audit trail.
    """

    __tablename__ = "project_files"
    __table_args__ = (
        CheckConstraint(sql_in("kind", FILE_KINDS), name="kind_valid"),
        CheckConstraint(sql_in("detected_type", FILE_TYPES), name="detected_type_valid"),
        CheckConstraint(sql_in("scan_status", FILE_SCAN_STATUSES), name="scan_status_valid"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("version_number >= 1", name="version_positive"),
        UniqueConstraint("series_id", "version_number"),
        Index("ix_project_files_project_id", "project_id"),
        Index("ix_project_files_series_id", "series_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    # Versions of the same document share a series; the first version's id is the series id.
    series_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, default=uuid.uuid4)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Marks the version that takeoff/estimate work is based on (one per series).
    is_basis: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    restored_from_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_files.id"), nullable=True
    )
    original_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ownership: Mapped[str | None] = mapped_column(String(200), nullable=True)
    detected_type: Mapped[str] = mapped_column(String(10), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scan_status: Mapped[str] = mapped_column(String(20), nullable=False)
    scan_detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


class AdminAuditEvent(Base):
    """Append-only record of a platform administrator action (ADMIN-001).

    Unlike ``ActivityEvent`` it is not tied to one project: it records who did what
    to which user or project, in the same transaction as the change.
    """

    __tablename__ = "admin_audit_events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    target_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
