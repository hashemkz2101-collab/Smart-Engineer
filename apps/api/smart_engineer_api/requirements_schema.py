"""Client requirement inputs (REQ-001, REQ-002, REQ-003; master spec 3.4).

* ``program``: unit and floor counts, target area or range, and a list of rooms /
  named spaces with counts, types and area targets or ranges.
* ``preferences``: accessibility, privacy, style, quality, budget and priorities,
  mandatory / preferred / unacceptable constraints, expansion and change of use,
  each recorded independently.
* ``references``: reference examples with label and explanation (and an optional
  link, and an optional ``file_id`` that points to a file uploaded to the same project).

Only supplied values are stored. Omitted values are never defaulted; an explicitly
empty list means "none".
"""

import uuid

from .intake_schema import Field
from .roles import REQUIREMENT_SECTIONS
from .site_schema import ListField, clean_document


def _num(minimum: float, maximum: float, required: bool = False) -> Field:
    return Field("number", minimum=minimum, maximum=maximum, required=required)


def _int(minimum: int, maximum: int, required: bool = False) -> Field:
    return Field("integer", minimum=minimum, maximum=maximum, required=required)


def _text(length: int = 1000, required: bool = False) -> Field:
    return Field("text", max_length=length, required=required)


ROOM_KINDS = (
    "bedroom",
    "master_bedroom",
    "kitchen",
    "reception",
    "living",
    "bathroom",
    "wc",
    "storage",
    "laundry",
    "office",
    "special",
    "parking",
    "yard",
    "terrace",
    "balcony",
    "roof_garden",
    "green_space",
    "other",
)
ACCESSIBILITY = ("none", "older_occupants", "disabled_occupants", "both")
LEVELS = ("low", "medium", "high")
SEPARATION = ("not_needed", "preferred", "required")
QUALITY = ("economic", "standard", "high", "luxury")
CURRENCIES = ("toman", "rial")
BUDGET_FLEXIBILITY = ("fixed", "flexible")
CONSTRAINT_LEVELS = ("mandatory", "preferred", "unacceptable")
REFERENCE_KINDS = ("image", "example_project", "other")

SCHEMA: dict[str, dict[str, Field | ListField]] = {
    "program": {
        "units_count": _int(1, 1000, True),
        "floors_count": _int(1, 300, True),
        "target_area_m2": _num(1, 1e9),
        "target_area_min_m2": _num(1, 1e9),
        "target_area_max_m2": _num(1, 1e9),
        "rooms": ListField(
            {
                "kind": Field("choice", choices=ROOM_KINDS, required=True),
                "name": _text(200),
                "count": _int(1, 1000),
                "target_area_m2": _num(0.1, 1e6),
                "area_min_m2": _num(0.1, 1e6),
                "area_max_m2": _num(0.1, 1e6),
                "notes": _text(),
            },
            max_items=300,
            required=True,
        ),
    },
    "preferences": {
        "accessibility": Field("choice", choices=ACCESSIBILITY),
        "accessibility_notes": _text(),
        "privacy_level": Field("choice", choices=LEVELS),
        "public_private_separation": Field("choice", choices=SEPARATION),
        "privacy_notes": _text(),
        "style": _text(300),
        "quality_level": Field("choice", choices=QUALITY),
        "material_level": Field("choice", choices=QUALITY),
        "material_notes": _text(),
        "budget_amount": _num(0, 1e15),
        "budget_currency": Field("choice", choices=CURRENCIES),
        "budget_flexibility": Field("choice", choices=BUDGET_FLEXIBILITY),
        "priorities": ListField({"item": _text(300, True), "rank": _int(1, 100)}, max_items=50),
        "constraints": ListField(
            {
                "level": Field("choice", choices=CONSTRAINT_LEVELS, required=True),
                "description": _text(500, True),
            },
            max_items=200,
        ),
        "future_expansion": _text(),
        "change_of_use": _text(),
    },
    "references": {
        "items": ListField(
            {
                "label": _text(200, True),
                "explanation": _text(),
                "kind": Field("choice", choices=REFERENCE_KINDS),
                "url": _text(500),
                "file_id": _text(36),
            },
            max_items=100,
            required=True,
        ),
    },
}

assert set(SCHEMA) == set(REQUIREMENT_SECTIONS)


def _range_errors(owner: dict, errors: dict[str, str], prefix: str, low: str, high: str) -> None:
    if low in owner and high in owner and owner[low] > owner[high]:
        errors[f"{prefix}{high}"] = "range_inverted"


def validate_section(section: str, data: dict) -> tuple[dict, dict[str, str]]:
    cleaned, errors = clean_document(SCHEMA[section], data)
    if section == "program":
        _range_errors(cleaned, errors, "", "target_area_min_m2", "target_area_max_m2")
        for index, room in enumerate(cleaned.get("rooms", [])):
            _range_errors(room, errors, f"rooms[{index}].", "area_min_m2", "area_max_m2")
    elif section == "preferences":
        if "budget_amount" in cleaned and "budget_currency" not in cleaned:
            errors["budget_currency"] = "currency_required"
    elif section == "references":
        for index, item in enumerate(cleaned.get("items", [])):
            url = item.get("url")
            if url is not None and not url.startswith(("http://", "https://")):
                errors[f"items[{index}].url"] = "invalid_url"
            file_id = item.get("file_id")
            if file_id is not None:
                try:
                    uuid.UUID(file_id)
                except ValueError:
                    errors[f"items[{index}].file_id"] = "invalid_file_id"
    return cleaned, errors


def missing_required(section: str, cleaned: dict) -> list[str]:
    return [name for name, spec in SCHEMA[section].items() if spec.required and name not in cleaned]


def not_provided(section: str, cleaned: dict) -> list[str]:
    return [
        name for name, spec in SCHEMA[section].items() if not spec.required and name not in cleaned
    ]
