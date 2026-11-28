"""Claude design proposals for a project's working design (advisory; see ai_design)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import layout_service
from .access import authorize_project
from .ai_design import MAX_INSTRUCTION_LENGTH, AiClient, AiError, build_context, propose
from .config import Settings
from .db import ActivityEvent, DesignModel, SpaceSchedule, User
from .design_service import DesignServiceError

DAILY_PROPOSAL_LIMIT = 30


def ai_status(settings: Settings, client: AiClient | None) -> dict:
    return {"enabled": client is not None,
            "model": settings.anthropic_model if client is not None else None}


def propose_design(
    session: Session,
    actor: User,
    project_id: uuid.UUID,
    *,
    client: AiClient | None,
    settings: Settings,
    instruction: str,
) -> dict:
    authorize_project(session, actor, project_id, "project.design.edit")
    if client is None:
        raise AiError("ai_not_configured")
    instruction = instruction.strip() if isinstance(instruction, str) else ""
    if len(instruction) > MAX_INSTRUCTION_LENGTH:
        raise DesignServiceError("invalid_value")
    row = session.scalar(
        select(DesignModel)
        .where(DesignModel.project_id == project_id)
        .execution_options(populate_existing=True)
    )
    if row is None or not row.data.get("elements"):
        raise DesignServiceError("no_design")
    since = datetime.now(UTC) - timedelta(days=1)
    used = session.scalar(
        select(func.count(ActivityEvent.id)).where(
            ActivityEvent.project_id == project_id,
            ActivityEvent.action == "project.design_ai_proposed",
            ActivityEvent.created_at >= since,
        )
    )
    if used >= DAILY_PROPOSAL_LIMIT:
        raise AiError("ai_limit_reached")
    inputs = layout_service._inputs(session, project_id)
    schedule: SpaceSchedule | None = inputs["schedule"]
    spaces = schedule.data.get("spaces", []) if schedule else []
    context = build_context(row.data, inputs["report"].get("envelope"), spaces)
    base_version, design = row.version, row.data
    result = propose(client, context, instruction, design)
    session.add(
        ActivityEvent(
            project_id=project_id,
            actor_user_id=actor.id,
            action="project.design_ai_proposed",
            detail={"valid": result["valid"], "operations": len(result["operations"]),
                    "attempts": result["attempts"]},
        )
    )
    session.commit()
    return {"base_version": base_version, "model": settings.anthropic_model, **result}
