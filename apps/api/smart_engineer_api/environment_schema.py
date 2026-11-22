"""Environmental and technical-condition inputs with sources (ENV-001, spec 3.5).

Climate, solar exposure, prevailing wind, rainfall, design temperature and comfort,
natural hazards, seismicity, utility availability (water, electricity, gas, sewer,
telecom) and energy constraints. Each record keeps the values the user entered plus
where they come from: source type, title or reference, the location the data
applies to, and a date (Jalali or Gregorian) with an explicit "source verified"
statement. Status is derived: no values -> ``unknown``; values without a complete
verified source, location and date -> ``needs_inquiry``; otherwise ``verified``.
Nothing is defaulted and nothing is produced by AI.
"""

from .intake_schema import Field
from .roles import ENV_FIELDS
from .site_schema import _clean_scalar
from .zoning_schema import _valid_date


def _num(minimum: float, maximum: float) -> Field:
    return Field("number", minimum=minimum, maximum=maximum)


def _text(length: int = 1000) -> Field:
    return Field("text", max_length=length)


SOURCE_TYPES = (
    "meteorological_station",
    "national_standard",
    "official_map",
    "utility_company",
    "municipality",
    "site_survey",
    "report",
    "other",
)
CALENDARS = ("gregorian", "jalali")
DIRECTIONS = (
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
)
RISK = ("none", "low", "medium", "high")
AVAILABILITY = ("available", "not_available", "planned")

SOURCE_FIELDS: dict[str, Field] = {
    "source_type": Field("choice", choices=SOURCE_TYPES),
    "source_title": _text(300),
    "source_reference": _text(500),
    "location_reference": _text(300),
    "source_date": _text(10),
    "source_calendar": Field("choice", choices=CALENDARS),
    "source_verified": Field("boolean"),
}


def _utility() -> dict[str, Field]:
    return {
        "availability": Field("choice", choices=AVAILABILITY),
        "connection_distance_m": _num(0, 1e6),
        "notes": _text(),
    }


VALUE_FIELDS: dict[str, dict[str, Field]] = {
    "climate": {
        "climate_zone": _text(200),
        "mean_annual_temperature_c": _num(-60, 70),
        "climate_notes": _text(),
    },
    "solar": {
        "solar_radiation_kwh_m2_day": _num(0, 15),
        "sunshine_hours_per_year": _num(0, 4500),
        "solar_notes": _text(),
    },
    "wind": {
        "prevailing_direction": Field("choice", choices=DIRECTIONS),
        "mean_speed_ms": _num(0, 100),
        "wind_notes": _text(),
    },
    "rainfall": {
        "annual_mm": _num(0, 20000),
        "max_daily_mm": _num(0, 2000),
        "rainfall_notes": _text(),
    },
    "design_temperature": {
        "summer_design_c": _num(-60, 70),
        "winter_design_c": _num(-80, 60),
        "comfort_notes": _text(),
    },
    "hazards": {
        "flood_risk": Field("choice", choices=RISK),
        "landslide_risk": Field("choice", choices=RISK),
        "subsidence_risk": Field("choice", choices=RISK),
        "other_hazards": _text(),
    },
    "seismicity": {
        "seismic_zone": _text(200),
        "design_pga_g": _num(0, 3),
        "nearest_fault_km": _num(0, 5000),
        "seismic_notes": _text(),
    },
    "water": _utility(),
    "electricity": _utility(),
    "gas": _utility(),
    "sewer": _utility(),
    "telecom": _utility(),
    "energy": {
        "energy_constraints": _text(2000),
        "efficiency_requirements": _text(2000),
    },
}

assert set(VALUE_FIELDS) == set(ENV_FIELDS)


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
    if (
        field == "design_temperature"
        and "summer_design_c" in cleaned
        and "winter_design_c" in cleaned
    ):
        if cleaned["winter_design_c"] > cleaned["summer_design_c"]:
            errors["winter_design_c"] = "winter_above_summer"
    return cleaned, errors


def derive_status(field: str, cleaned: dict) -> dict:
    """Return the status and the source parts still missing."""
    if not any(name in cleaned for name in VALUE_FIELDS[field]):
        return {"status": "unknown", "source_missing": []}
    missing: list[str] = []
    if "source_type" not in cleaned:
        missing.append("source_type")
    if "source_title" not in cleaned and "source_reference" not in cleaned:
        missing.append("source_title_or_reference")
    if "location_reference" not in cleaned:
        missing.append("location_reference")
    if "source_date" not in cleaned:
        missing.append("source_date")
    if missing or cleaned.get("source_verified") is not True:
        return {"status": "needs_inquiry", "source_missing": missing}
    return {"status": "verified", "source_missing": []}
