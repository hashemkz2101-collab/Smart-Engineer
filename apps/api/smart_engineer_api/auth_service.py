"""Authentication service (IAM-001, DEC-022). No HTTP concerns live here.

Every public function takes a SQLAlchemy ``Session`` and **commits its own
work**, including the failure records written before an ``AuthError`` is raised,
so a failed login still counts toward the lockout. ``now`` is injectable so time
rules are testable without sleeping.
"""

import hmac
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import AuthSession, AuthToken, LoginFailure, Membership, Organization, User
from .security import (
    DEFAULT_SCRYPT,
    ScryptParams,
    hash_password,
    new_token,
    normalize_email,
    password_problems,
    token_digest,
    verify_password,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    """A rejected authentication action. ``code`` is stable and safe to expose."""

    def __init__(self, code: str, problems: list[str] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.problems = problems or []


@dataclass(frozen=True, slots=True)
class AuthPolicy:
    session_absolute: timedelta = timedelta(days=14)
    session_idle: timedelta = timedelta(hours=24)
    max_failures: int = 5
    failure_window: timedelta = timedelta(minutes=15)
    reset_ttl: timedelta = timedelta(hours=1)
    verification_ttl: timedelta = timedelta(hours=24)
    # A repeated "send again" inside this window is ignored, so the endpoint cannot be
    # used to flood a mailbox.
    verification_cooldown: timedelta = timedelta(seconds=60)
    require_email_verification: bool = False
    scrypt: ScryptParams = field(default=DEFAULT_SCRYPT)


class Mailer(Protocol):
    def send_password_reset(self, email: str, token: str) -> None: ...

    def send_email_verification(self, email: str, token: str) -> None: ...


@dataclass(slots=True)
class OutboxMailer:
    """Collects messages in memory: used in tests and when no SMTP server is configured."""

    password_resets: list[tuple[str, str]] = field(default_factory=list)
    email_verifications: list[tuple[str, str]] = field(default_factory=list)

    def send_password_reset(self, email: str, token: str) -> None:
        self.password_resets.append((email, token))

    def send_email_verification(self, email: str, token: str) -> None:
        self.email_verifications.append((email, token))


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    csrf_token: str
    user: User


def utcnow() -> datetime:
    return datetime.now(UTC)


def aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _dummy_hash(policy: AuthPolicy) -> str:
    return hash_password("not-a-real-password", policy.scrypt)


def register(
    session: Session,
    policy: AuthPolicy,
    *,
    email: str,
    display_name: str,
    password: str,
    now: datetime | None = None,
) -> User:
    """Create a user plus a personal organization the user owns (DEC-017)."""
    email = normalize_email(email)
    display_name = display_name.strip()
    if not EMAIL_PATTERN.match(email) or len(email) > 320:
        raise AuthError("invalid_email")
    if not display_name or len(display_name) > 200:
        raise AuthError("invalid_display_name")
    problems = password_problems(password, email)
    if problems:
        raise AuthError("weak_password", problems)
    if session.scalar(select(User.id).where(User.email == email)) is not None:
        raise AuthError("email_taken")

    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password(password, policy.scrypt),
    )
    organization = Organization(name=display_name)
    session.add_all([user, organization])
    try:
        session.flush()
        session.add(
            Membership(organization_id=organization.id, user_id=user.id, org_role="owner")
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise AuthError("email_taken") from None
    return user


def _recent_failures(session: Session, policy: AuthPolicy, email: str, now: datetime) -> int:
    since = now - policy.failure_window
    return session.scalar(
        select(func.count())
        .select_from(LoginFailure)
        .where(LoginFailure.email == email, LoginFailure.created_at > since)
    )


def login(
    session: Session,
    policy: AuthPolicy,
    *,
    email: str,
    password: str,
    now: datetime | None = None,
) -> IssuedSession:
    now = now or utcnow()
    email = normalize_email(email)
    if _recent_failures(session, policy, email, now) >= policy.max_failures:
        raise AuthError("account_locked")

    user = session.scalar(select(User).where(User.email == email))
    # Always run one password verification so timing does not reveal whether the
    # email exists.
    stored = user.password_hash if user is not None else _dummy_hash(policy)
    matches = verify_password(password, stored)
    if user is None or not matches or not user.is_active:
        session.add(LoginFailure(email=email, created_at=now))
        session.commit()
        raise AuthError("invalid_credentials")
    if policy.require_email_verification and user.email_verified_at is None:
        raise AuthError("email_not_verified")

    session.execute(delete(LoginFailure).where(LoginFailure.email == email))
    user.last_login_at = now
    token = new_token()
    csrf = new_token()
    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_digest(token),
            csrf_token=csrf,
            created_at=now,
            last_seen_at=now,
            expires_at=now + policy.session_absolute,
        )
    )
    session.commit()
    return IssuedSession(token=token, csrf_token=csrf, user=user)


def authenticate(
    session: Session, policy: AuthPolicy, token: str, now: datetime | None = None
) -> tuple[AuthSession, User] | None:
    """Return the live session and user for a cookie token, or None."""
    now = now or utcnow()
    record = session.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_digest(token))
    )
    if record is None or record.revoked_at is not None:
        return None
    if aware(record.expires_at) <= now:
        return None
    if aware(record.last_seen_at) + policy.session_idle <= now:
        return None
    user = session.get(User, record.user_id)
    if user is None or not user.is_active:
        return None
    record.last_seen_at = now
    session.commit()
    return record, user


def csrf_matches(record: AuthSession, presented: str | None) -> bool:
    return bool(presented) and hmac.compare_digest(record.csrf_token, presented)


def logout(session: Session, token: str, now: datetime | None = None) -> None:
    now = now or utcnow()
    session.execute(
        update(AuthSession)
        .where(AuthSession.token_hash == token_digest(token), AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    session.commit()


def _revoke_sessions(
    session: Session, user_id, now: datetime, keep_session_id=None
) -> None:
    statement = update(AuthSession).where(
        AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
    )
    if keep_session_id is not None:
        statement = statement.where(AuthSession.id != keep_session_id)
    session.execute(statement.values(revoked_at=now))


def change_password(
    session: Session,
    policy: AuthPolicy,
    user: User,
    *,
    current_password: str,
    new_password: str,
    keep_session_id=None,
    now: datetime | None = None,
) -> None:
    now = now or utcnow()
    if not verify_password(current_password, user.password_hash):
        raise AuthError("invalid_credentials")
    problems = password_problems(new_password, user.email)
    if problems:
        raise AuthError("weak_password", problems)
    user.password_hash = hash_password(new_password, policy.scrypt)
    _revoke_sessions(session, user.id, now, keep_session_id)
    session.commit()


def request_password_reset(
    session: Session,
    policy: AuthPolicy,
    mailer: Mailer,
    *,
    email: str,
    now: datetime | None = None,
) -> None:
    """Never reveals whether the email exists: it returns None in every case."""
    now = now or utcnow()
    email = normalize_email(email)
    user = session.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        return
    session.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == "password_reset",
            AuthToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    token = new_token()
    session.add(
        AuthToken(
            user_id=user.id,
            purpose="password_reset",
            token_hash=token_digest(token),
            created_at=now,
            expires_at=now + policy.reset_ttl,
        )
    )
    session.commit()
    mailer.send_password_reset(user.email, token)


def reset_password(
    session: Session,
    policy: AuthPolicy,
    *,
    token: str,
    new_password: str,
    now: datetime | None = None,
) -> None:
    now = now or utcnow()
    record = session.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == token_digest(token),
            AuthToken.purpose == "password_reset",
        )
    )
    if record is None or record.used_at is not None or aware(record.expires_at) <= now:
        raise AuthError("invalid_token")
    user = session.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthError("invalid_token")
    problems = password_problems(new_password, user.email)
    if problems:
        raise AuthError("weak_password", problems)
    user.password_hash = hash_password(new_password, policy.scrypt)
    record.used_at = now
    _revoke_sessions(session, user.id, now)
    session.execute(delete(LoginFailure).where(LoginFailure.email == user.email))
    session.commit()


def request_email_verification(
    session: Session,
    policy: AuthPolicy,
    mailer: Mailer,
    *,
    email: str,
    now: datetime | None = None,
) -> None:
    """Send a confirmation link. Never reveals whether the email exists or is verified."""
    now = now or utcnow()
    user = session.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not user.is_active or user.email_verified_at is not None:
        return
    recent = session.scalar(
        select(AuthToken.id).where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == "email_verification",
            AuthToken.used_at.is_(None),
            AuthToken.created_at > now - policy.verification_cooldown,
        )
    )
    if recent is not None:
        return
    session.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == "email_verification",
            AuthToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    token = new_token()
    session.add(
        AuthToken(
            user_id=user.id,
            purpose="email_verification",
            token_hash=token_digest(token),
            created_at=now,
            expires_at=now + policy.verification_ttl,
        )
    )
    session.commit()
    mailer.send_email_verification(user.email, token)


def confirm_email(session: Session, *, token: str, now: datetime | None = None) -> None:
    """Mark the address verified. Unknown, used, expired tokens all look the same."""
    now = now or utcnow()
    record = session.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == token_digest(token),
            AuthToken.purpose == "email_verification",
        )
    )
    if record is None or record.used_at is not None or aware(record.expires_at) <= now:
        raise AuthError("invalid_token")
    user = session.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthError("invalid_token")
    if user.email_verified_at is None:
        user.email_verified_at = now
    record.used_at = now
    session.commit()
