"""Demo accounts and sample projects for trying the app locally (Codespaces).

Only for a throwaway local database: it refuses to run in production or against a
database that is not on this machine. Everything here is invented; the password is
public on purpose and must never be used for a real account.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from . import admin_service, auth_service, org_service, project_service
from .config import ConfigurationError, Settings
from .db import Project, User

DEMO_DOMAIN = "demo.smart-engineer.test"  # reserved .test domain: can never be a real mailbox
DEMO_PASSWORD = "Demo Password 2026 Local"  # secret-scan:allow (public demo credential)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

ACCOUNTS = (
    # key, display name, project role in the sample projects (None = not added)
    ("owner", "مالک نمونه", "owner"),
    ("architect", "معمار نمونه", "architect"),
    ("structural", "مهندس سازهٔ نمونه", "structural_engineer"),
    ("qs", "مترور نمونه", "quantity_surveyor"),
    ("admin", "مدیر سامانهٔ نمونه", None),
)


def email_for(key: str) -> str:
    return f"{key}@{DEMO_DOMAIN}"


def ensure_local_demo_database(settings: Settings) -> None:
    """Refuse anything that could be a real installation."""
    if settings.environment == "production":
        raise ConfigurationError("The demo seed never runs in production.")
    if not settings.database_url:
        raise ConfigurationError("SMART_ENGINEER_DATABASE_URL is not set.")
    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite" and (url.host or "") not in LOCAL_HOSTS:
        raise ConfigurationError("The demo seed only runs against a database on this machine.")


def seed(session: Session, policy: auth_service.AuthPolicy | None = None) -> list[str]:
    """Create the demo data once; return the demo emails."""
    policy = policy or auth_service.AuthPolicy()
    emails = [email_for(key) for key, _, _ in ACCOUNTS]
    if session.scalar(select(User.id).where(User.email == email_for("owner"))) is not None:
        return emails

    users: dict[str, User] = {}
    for key, name, _ in ACCOUNTS:
        users[key] = auth_service.register(
            session, policy, email=email_for(key), display_name=name, password=DEMO_PASSWORD
        )
    admin_service.grant_first_admin(session, email_for("admin"))

    owner = users["owner"]
    organization = org_service.list_user_organizations(session, owner)[0][0]
    for key, _, role in ACCOUNTS:
        if role is None or key == "owner":
            continue
        _, token = org_service.create_invitation(
            session, owner, organization.id, email=email_for(key), org_role="member"
        )
        org_service.accept_invitation(session, users[key], token)

    samples = (
        ("خانهٔ ویلایی نمونه", "residential_house", "پروژهٔ آزمایشی برای امتحان صفحه‌ها."),
        ("مجتمع مسکونی نمونه", "residential_apartment", "پروژهٔ آزمایشی دوم."),
    )
    for name, kind, description in samples:
        project: Project = project_service.create_project(
            session, owner, organization.id, name=name, project_type=kind, description=description
        )
        for key, _, role in ACCOUNTS:
            if role is None or key == "owner":
                continue
            project_service.add_member(
                session, owner, uuid.UUID(str(project.id)), email=email_for(key), role=role
            )
    return emails
