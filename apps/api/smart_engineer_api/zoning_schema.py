"""Zoning / building-control inputs with source references (RULE-DATA-001).

Values are user-recorded inputs, never rules the system asserts. Every category
carries a source (type, date, title or reference) and an explicit "source verified"
statement. Status is derived: no values -> ``unknown``; values without a complete,
verified source -> ``needs_inquiry``; otherwise ``verified``. Nothing is defaulted
and nothing here is produced by AI (master spec 3.3.k).
"""

import datetime

from .intake_schema import Field
from .roles import ZONING_FIELDS
from .site_schema import _clean_scalar


def _num(minimum: float, maximum: float) -> Field:
    return Field("number", minimum=minimum, maximum=maximum)


def _int(minimum: int, maximum: int) -> Field:
    return Field("integer", minimum=minimum, maximum=maximum)


def _text(length: int = 1000) -> Field:
    return Field("text", max_length=length)


SOURCE_TYPES = (
    "municipality_letter",
    "master_plan",
    "detailed_plan",
    "permit_office_inquiry",
    "regulation_document",
    "other",
)
CALENDARS = ("gregorian", "jalali")

SOURCE_FIELDS: dict[str, Field] = {
    "source_type": Field("choice", choices=SOURCE_TYPES),
    "source_title": _text(300),
    "source_reference": _text(500),
    "source_date": _text(10),
    "source_calendar": Field("choice", choices=CALENDARS),
    "source_verified": Field("boolean"),
    "source_revision": _text(200),
    "valid_from": _text(10),
    "valid_until": _text(10),
}

VALUE_FIELDS: dict[str, dict[str, Field]] = {
    "land_use": {"zone_name": _text(200), "land_use": _text(200)},
    "coverage": {"max_coverage_percent": _num(0, 100)},
    "density": {"max_density_percent": _num(0, 5000), "max_floor_area_m2": _num(0, 1e9)},
    "floors_height": {"max_floors": _int(0, 300), "max_height_m": _num(0, 2000)},
    "setbacks": {
        "front_m": _num(0, 1000),
        "rear_m": _num(0, 1000),
        "left_m": _num(0, 1000),
        "right_m": _num(0, 1000),
        "correction_notes": _text(),
    },
    "parking_access": {
        "min_parking_spaces": _int(0, 100000),
        "parking_notes": _text(),
        "access_notes": _text(),
    },
    "daylight_openings": {
        "daylight_notes": _text(),
        "courtyard_notes": _text(),
        "opening_notes": _text(),
    },
    "circulation": {
        "elevator": Field("choice", choices=("required", "not_required")),
        "stair_notes": _text(),
        "ramp_notes": _text(),
        "exit_notes": _text(),
    },
    "local_constraints": {"constraints": _text(2000)},
}

assert set(VALUE_FIELDS) == set(ZONING_FIELDS)


def _valid_date(text: str, calendar: str) -> bool:
    parts = text.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts) or len(parts[0]) != 4:
        return False
    year, month, day = (int(p) for p in parts)
    if calendar == "gregorian":
        try:
            datetime.date(year, month, day)
        except ValueError:
            return False
        return True
    if not 1200 <= year <= 1600 or not 1 <= month <= 12 or day < 1:
        return False
    return day <= (31 if month <= 6 else 30)


def validate_record(field: str, data: dict) -> tuple[dict, dict[str, str]]:
    specs = {**VALUE_FIELDS[field], **SOURCE_FIELDS}
    cleaned: dict = {}
    errors: dict[str, str] = {}
    for key, value in data.items():
        spec = specs.get(key)
        if spec is None:
            errors[key] = "unknown_field"
            continue
        result, reason = _clean_scalar(spec, value)
        if reason:
            errors[key] = reason
        elif result is not None:
            cleaned[key] = result
    if "source_date" in cleaned and "source_date" not in errors:
        calendar = cleaned.get("source_calendar")
        if calendar is None:
            errors["source_calendar"] = "calendar_required"
        elif not _valid_date(cleaned["source_date"], calendar):
            errors["source_date"] = "invalid_date"
    for name in ("valid_from", "valid_until"):
        if name in cleaned:
            try:
                datetime.date.fromisoformat(cleaned[name])
            except ValueError:
                errors[name] = "invalid_date"
    validity_complete = all(k in cleaned and k not in errors for k in ("valid_from", "valid_until"))
    if validity_complete:
        start = datetime.date.fromisoformat(cleaned["valid_from"])
        end = datetime.date.fromisoformat(cleaned["valid_until"])
        if start > end:
            errors["valid_until"] = "range_inverted"
    return cleaned, errors


def derive_status(field: str, cleaned: dict) -> dict:
    """Return the status and the source parts still missing."""
    has_values = any(name in cleaned for name in VALUE_FIELDS[field])
    missing: list[str] = []
    if not has_values:
        return {"status": "unknown", "source_missing": []}
    if "source_type" not in cleaned:
        missing.append("source_type")
    if "source_date" not in cleaned:
        missing.append("source_date")
    if "source_title" not in cleaned and "source_reference" not in cleaned:
        missing.append("source_title_or_reference")
    if missing or cleaned.get("source_verified") is not True:
        return {"status": "needs_inquiry", "source_missing": missing}
    return {"status": "verified", "source_missing": []}
