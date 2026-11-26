"""Project-scoped geometry reports; site/zoning records remain the source of truth."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import authorize_project
from .db import SiteSection, User, ZoningRecord
from .geometry import ENGINE_VERSION, GeometryError, analyze, buildable_envelope, canonicalize
from .site_schema import validate_section
from .site_service import SiteValidationError


def _records(session: Session, project_id: uuid.UUID) -> tuple[dict, dict]:
    site = {row.section_key: row for row in session.scalars(
        select(SiteSection).where(SiteSection.project_id == project_id)
        .execution_options(populate_existing=True)
    )}
    zoning = {row.field_key: row for row in session.scalars(
        select(ZoningRecord).where(ZoningRecord.project_id == project_id)
        .execution_options(populate_existing=True)
    )}
    return site, zoning


def _report(data: dict, site: dict, zoning: dict) -> dict:
    versions = {
        "parcel": site["parcel"].version if "parcel" in site else 0,
        "access": site["access"].version if "access" in site else 0,
        "setbacks": zoning["setbacks"].version if "setbacks" in zoning else 0,
        "coverage": zoning["coverage"].version if "coverage" in zoning else 0,
    }
    try:
        result = analyze(data, site["access"].data if "access" in site else {})
        result["envelope"] = buildable_envelope(
            data, zoning["setbacks"].data if "setbacks" in zoning else {},
            zoning["coverage"].data if "coverage" in zoning else {},
        )
    except GeometryError as exc:
        result = {"status": "invalid" if data else "incomplete", "engine_version": ENGINE_VERSION,
                  "errors": [{"field": exc.field, "reason": exc.code}], "envelope": None}
    result["source_versions"] = versions
    return result


def get_geometry(session: Session, actor: User, project_id: uuid.UUID) -> dict:
    authorize_project(session, actor, project_id, "project.view")
    site, zoning = _records(session, project_id)
    return _report(site["parcel"].data if "parcel" in site else {}, site, zoning)


def preview_geometry(
    session: Session, actor: User, project_id: uuid.UUID, data: dict, unit: str,
) -> dict:
    authorize_project(session, actor, project_id, "project.site.edit")
    canonical = canonicalize(data, unit)
    cleaned, errors = validate_section("parcel", canonical)
    if errors:
        raise SiteValidationError(errors)
    # Preview must not disguise an invalid/incomplete polygon as valid coordinates.
    analyze(cleaned)
    site, zoning = _records(session, project_id)
    result = _report(cleaned, site, zoning)
    result["canonical_data"] = cleaned
    result["preview"] = True
    return result
