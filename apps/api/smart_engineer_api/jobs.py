"""Background-job lifecycle with an explicit state machine.

Each job records its status, versioned input, result or error, attempts, and
start/end times. Error text must never contain secrets; it is truncated here
but not sanitised, so callers pass a short, safe message.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .db import BackgroundJob

MAX_ERROR_LENGTH = 2000

TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"running", "cancelled"}),
    "running": frozenset({"succeeded", "failed", "cancelled"}),
    "failed": frozenset({"queued"}),
    "succeeded": frozenset(),
    "cancelled": frozenset(),
}


class InvalidJobTransition(ValueError):
    """Raised when a job is moved to a status its current status does not allow."""


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _move(job: BackgroundJob, new_status: str) -> None:
    if new_status not in TRANSITIONS.get(job.status, frozenset()):
        raise InvalidJobTransition(f"Cannot change a job from {job.status} to {new_status}.")
    job.status = new_status


def create_job(
    session: Session,
    job_type: str,
    payload: dict | None = None,
    *,
    input_version: int = 1,
) -> BackgroundJob:
    if not job_type:
        raise ValueError("job_type is required.")
    if input_version < 1:
        raise ValueError("input_version must be at least 1.")
    job = BackgroundJob(
        job_type=job_type,
        payload=payload or {},
        input_version=input_version,
        status="queued",
        attempts=0,
    )
    session.add(job)
    session.flush()
    return job


def start_job(session: Session, job: BackgroundJob, *, now: datetime | None = None) -> None:
    _move(job, "running")
    job.attempts += 1
    job.started_at = _now(now)
    job.finished_at = None
    job.last_error = None
    session.flush()


def succeed_job(
    session: Session,
    job: BackgroundJob,
    result: dict | None = None,
    *,
    now: datetime | None = None,
) -> None:
    _move(job, "succeeded")
    job.result = result if result is not None else {}
    job.finished_at = _now(now)
    session.flush()


def fail_job(
    session: Session, job: BackgroundJob, error: str, *, now: datetime | None = None
) -> None:
    _move(job, "failed")
    job.last_error = error[:MAX_ERROR_LENGTH]
    job.finished_at = _now(now)
    session.flush()


def cancel_job(session: Session, job: BackgroundJob, *, now: datetime | None = None) -> None:
    _move(job, "cancelled")
    job.finished_at = _now(now)
    session.flush()


def retry_job(session: Session, job: BackgroundJob) -> None:
    """Re-queue a failed job; the previous error stays until the next start."""
    _move(job, "queued")
    job.finished_at = None
    session.flush()
