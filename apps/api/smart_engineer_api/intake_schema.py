"""Field definitions and validation for the project intake steps (INP-002).

Legal-status fields are free text or simple choices recorded as the user states
them. Nothing here checks or asserts legal validity (master spec 3.1).
"""

from dataclasses import dataclass

from .roles import INTAKE_STEPS

PURPOSES = ("residence", "investment", "sale", "rent", "mixed_use")
OWNERSHIP_STATUSES = ("unknown", "owned", "leased", "partnership", "other")
DEED_STATUSES = ("unknown", "has_deed", "no_deed", "in_process")


@dataclass(frozen=True, slots=True)
class Field:
    kind: str  # "text" | "choice" | "number"
    max_length: int = 0
    choices: tuple[str, ...] = ()
    minimum: float = 0.0
    maximum: float = 0.0
    required: bool = False


SCHEMA: dict[str, dict[str, Field]] = {
    "identity": {
        "project_code": Field("text", max_length=50),
        "purpose": Field("choice", choices=PURPOSES, required=True),
    },
    "location": {
        "province": Field("text", max_length=100, required=True),
        "city": Field("text", max_length=100, required=True),
        "address": Field("text", max_length=1000),
        "latitude": Field("number", minimum=-90, maximum=90),
        "longitude": Field("number", minimum=-180, maximum=180),
    },
    "people": {
        "client": Field("text", max_length=200, required=True),
        "owner": Field("text", max_length=200),
        "responsible_engineer": Field("text", max_length=200),
        "team_notes": Field("text", max_length=2000),
    },
    "legal": {
        "ownership_status": Field("choice", choices=OWNERSHIP_STATUSES),
        "deed_status": Field("choice", choices=DEED_STATUSES),
        "restrictions": Field("text", max_length=2000),
        "notes": Field("text", max_length=2000),
    },
}

assert set(SCHEMA) == set(INTAKE_STEPS)


def _clean(field: Field, value: object) -> tuple[object | None, str | None]:
    """Return (cleaned value or None when empty, error reason or None)."""
    if value is None:
        return None, None
    if field.kind == "number":
        if isinstance(value, bool):
            return None, "not_a_number"
        if isinstance(value, str):
            if not value.strip():
                return None, None
            try:
                value = float(value)
            except ValueError:
                return None, "not_a_number"
        if not isinstance(value, int | float):
            return None, "not_a_number"
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return None, "not_a_number"
        if not field.minimum <= number <= field.maximum:
            return None, "out_of_range"
        return number, None
    if not isinstance(value, str):
        return None, "not_text"
    text = value.strip()
    if not text:
        return None, None
    if field.kind == "choice":
        return (text, None) if text in field.choices else (None, "invalid_choice")
    if len(text) > field.max_length:
        return None, "too_long"
    return text, None


def validate_step(step: str, data: dict) -> tuple[dict, dict[str, str]]:
    """Return (cleaned data without empty fields, {field: reason}) for a step."""
    fields = SCHEMA[step]
    cleaned: dict = {}
    errors: dict[str, str] = {}
    for key, value in data.items():
        field = fields.get(key)
        if field is None:
            errors[key] = "unknown_field"
            continue
        result, reason = _clean(field, value)
        if reason:
            errors[key] = reason
        elif result is not None:
            cleaned[key] = result
    if step == "location" and "latitude" not in errors and "longitude" not in errors:
        if ("latitude" in cleaned) != ("longitude" in cleaned):
            missing = "longitude" if "latitude" in cleaned else "latitude"
            errors[missing] = "coordinates_need_both"
    return cleaned, errors


def missing_required(step: str, cleaned: dict) -> list[str]:
    return [
        name for name, field in SCHEMA[step].items() if field.required and name not in cleaned
    ]
