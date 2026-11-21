"""Field definitions, validation and derived geometry for site / land data.

SITE-001 (parcel, survey, orientation, access, terrain) and SITE-002
(surroundings, existing features, optional soil data).

Rules:
* Only values the user supplied are stored. Omitted optional values are never
  defaulted; ``not_provided`` reports them (soil especially).
* An explicitly empty list is kept and means "the user states there are none".
* Areas are computed from the entered geometry and compared with the declared
  area; the difference is always reported. Nothing here asserts legal or
  surveying validity of the numbers.
"""

import math
from dataclasses import dataclass, field

from .intake_schema import Field, _clean
from .roles import SITE_SECTIONS

# Development default (not a regulation): relative difference above which the
# declared and computed areas are reported as a discrepancy.
AREA_TOLERANCE_PERCENT = 1.0

SHAPES = ("rectangular", "polygon", "irregular")
SIDES = ("north", "south", "east", "west")
DIRECTIONS = (*SIDES, "northeast", "northwest", "southeast", "southwest")
TOPOGRAPHY = ("flat", "gentle_slope", "steep_slope", "terraced", "irregular")
NEIGHBOR_KINDS = ("building", "vacant_land", "road", "other")
BARRIERS = ("none", "wall", "fence", "other")
UTILITIES = ("water", "electricity", "gas", "sewage", "telecom", "other")
SOIL_TYPES = ("rock", "gravel", "sand", "silt", "clay", "mixed", "other")

COORD = dict(minimum=-1e7, maximum=1e7)


def _num(minimum: float, maximum: float, required: bool = False) -> Field:
    return Field("number", minimum=minimum, maximum=maximum, required=required)


def _int(minimum: int, maximum: int, required: bool = False) -> Field:
    return Field("integer", minimum=minimum, maximum=maximum, required=required)


@dataclass(frozen=True, slots=True)
class ListField:
    items: dict[str, Field]
    max_items: int = 100
    required: bool = False


def _described(extra: dict[str, Field] | None = None) -> dict[str, Field]:
    items = {
        "description": Field("text", max_length=300, required=True),
        "notes": Field("text", max_length=1000),
    }
    items.update(extra or {})
    return items


SCHEMA: dict[str, dict[str, Field | ListField]] = {
    "parcel": {
        "shape": Field("choice", choices=SHAPES, required=True),
        "width_m": _num(0.01, 100000),
        "depth_m": _num(0.01, 100000),
        "declared_area_m2": _num(0.01, 1e9),
        "vertices": ListField(
            {
                "x": Field("number", required=True, **COORD),
                "y": Field("number", required=True, **COORD),
            },
            max_items=200,
        ),
        "sides": ListField(
            {"label": Field("text", max_length=100), "length_m": _num(0.01, 100000, True)},
            max_items=200,
        ),
        "survey_reference": Field("text", max_length=500),
        "coordinate_system": Field("text", max_length=100),
        "survey_points": ListField(
            {
                "label": Field("text", max_length=100),
                "x": Field("number", required=True, **COORD),
                "y": Field("number", required=True, **COORD),
            },
            max_items=500,
        ),
    },
    "access": {
        "north_angle_deg": _num(0, 360),
        "street_direction": Field("choice", choices=DIRECTIONS, required=True),
        "frontage_length_m": _num(0.01, 100000),
        "road_width_m": _num(0.01, 500, True),
        "access_fronts": _int(0, 10, True),
    },
    "terrain": {
        "topography": Field("choice", choices=TOPOGRAPHY, required=True),
        "slope_percent": _num(0, 100),
        "level_difference_m": _num(-500, 500),
        "elevation_m": _num(-500, 9000),
    },
    "surroundings": {
        "neighbors": ListField(
            {
                "side": Field("choice", choices=SIDES, required=True),
                "kind": Field("choice", choices=NEIGHBOR_KINDS),
                "shared_wall": Field("boolean"),
                "barrier": Field("choice", choices=BARRIERS),
                "notes": Field("text", max_length=1000),
            },
            max_items=20,
            required=True,
        ),
        "trees": ListField(_described(), required=True),
        "wells": ListField(_described(), required=True),
        "channels": ListField(_described(), required=True),
        "existing_utilities": ListField(
            _described({"utility": Field("choice", choices=UTILITIES)}), required=True
        ),
        "easements": ListField(_described(), required=True),
    },
    "soil": {
        "soil_type": Field("choice", choices=SOIL_TYPES),
        "bearing_capacity_kpa": _num(1, 10000),
        "groundwater_depth_m": _num(0, 1000),
        "report_reference": Field("text", max_length=500),
    },
}

assert set(SCHEMA) == set(SITE_SECTIONS)


def _clean_scalar(spec: Field, value: object) -> tuple[object | None, str | None]:
    if spec.kind == "boolean":
        if value is None:
            return None, None
        return (value, None) if isinstance(value, bool) else (None, "not_a_boolean")
    if spec.kind == "integer":
        number, reason = _clean(Field("number", minimum=spec.minimum, maximum=spec.maximum), value)
        if reason or number is None:
            return number, reason
        return (int(number), None) if float(number).is_integer() else (None, "not_an_integer")
    return _clean(spec, value)


def _clean_list(spec: ListField, value: object, name: str, errors: dict[str, str]) -> list | None:
    if not isinstance(value, list):
        errors[name] = "not_a_list"
        return None
    if len(value) > spec.max_items:
        errors[name] = "too_many_items"
        return None
    cleaned_items: list[dict] = []
    for index, raw in enumerate(value):
        path = f"{name}[{index}]"
        if not isinstance(raw, dict):
            errors[path] = "not_an_object"
            continue
        item: dict = {}
        for key, item_value in raw.items():
            item_spec = spec.items.get(key)
            if item_spec is None:
                errors[f"{path}.{key}"] = "unknown_field"
                continue
            result, reason = _clean_scalar(item_spec, item_value)
            if reason:
                errors[f"{path}.{key}"] = reason
            elif result is not None:
                item[key] = result
        for key, item_spec in spec.items.items():
            if item_spec.required and key not in item and f"{path}.{key}" not in errors:
                errors[f"{path}.{key}"] = "required"
        cleaned_items.append(item)
    return cleaned_items


# --- geometry -------------------------------------------------------------------------


def polygon_area(points: list[tuple[float, float]]) -> float:
    """Absolute area by the shoelace formula (square units of the input)."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1], strict=True):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(p, q, r) -> bool:
    return min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])


def _segments_intersect(p1, p2, p3, p4) -> bool:
    d1, d2 = _cross(p3, p4, p1), _cross(p3, p4, p2)
    d3, d4 = _cross(p1, p2, p3), _cross(p1, p2, p4)
    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return True
    return (
        (d1 == 0 and _on_segment(p3, p1, p4))
        or (d2 == 0 and _on_segment(p3, p2, p4))
        or (d3 == 0 and _on_segment(p1, p3, p2))
        or (d4 == 0 and _on_segment(p1, p4, p2))
    )


def is_simple_polygon(points: list[tuple[float, float]]) -> bool:
    """True when no two non-adjacent edges touch or cross."""
    count = len(points)
    for i in range(count):
        a1, a2 = points[i], points[(i + 1) % count]
        for j in range(i + 1, count):
            if j == i or (j + 1) % count == i or (i + 1) % count == j:
                continue
            if _segments_intersect(a1, a2, points[j], points[(j + 1) % count]):
                return False
    return True


def _points(vertices: list[dict]) -> list[tuple[float, float]]:
    return [(float(v["x"]), float(v["y"])) for v in vertices]


# --- validation -----------------------------------------------------------------------


def validate_section(section: str, data: dict) -> tuple[dict, dict[str, str]]:
    """Return (cleaned data, {path: reason}). Empty scalars are dropped."""
    fields = SCHEMA[section]
    cleaned: dict = {}
    errors: dict[str, str] = {}
    for key, value in data.items():
        spec = fields.get(key)
        if spec is None:
            errors[key] = "unknown_field"
        elif isinstance(spec, ListField):
            result = _clean_list(spec, value, key, errors)
            if result is not None:
                cleaned[key] = result
        else:
            result, reason = _clean_scalar(spec, value)
            if reason:
                errors[key] = reason
            elif result is not None:
                cleaned[key] = result
    if section == "parcel":
        _check_parcel(cleaned, errors)
    return cleaned, errors


def _check_parcel(cleaned: dict, errors: dict[str, str]) -> None:
    vertices = cleaned.get("vertices")
    if vertices is None or any(k.startswith("vertices") for k in errors):
        return
    if 0 < len(vertices) < 3:
        errors["vertices"] = "too_few_points"
        return
    if len(vertices) >= 3:
        points = _points(vertices)
        if polygon_area(points) == 0:
            errors["vertices"] = "degenerate"
        elif not is_simple_polygon(points):
            errors["vertices"] = "self_intersecting"


def missing_required(section: str, cleaned: dict) -> list[str]:
    missing = [
        name
        for name, spec in SCHEMA[section].items()
        if spec.required and name not in cleaned
    ]
    if section == "parcel":
        shape = cleaned.get("shape")
        if shape == "rectangular":
            missing += [n for n in ("width_m", "depth_m") if n not in cleaned]
        elif shape in ("polygon", "irregular") and len(cleaned.get("vertices", [])) < 3:
            missing.append("vertices")
    return missing


def not_provided(section: str, cleaned: dict) -> list[str]:
    """Optional fields the user did not supply (never defaulted)."""
    return [
        name
        for name, spec in SCHEMA[section].items()
        if not spec.required and name not in cleaned
    ]


# --- derived values -------------------------------------------------------------------


@dataclass(slots=True)
class ParcelDerived:
    area_source: str | None = None
    computed_area_m2: float | None = None
    declared_area_m2: float | None = None
    difference_m2: float | None = None
    difference_percent: float | None = None
    status: str = "not_computable"
    tolerance_percent: float = AREA_TOLERANCE_PERCENT
    computed_side_lengths_m: list[float] = field(default_factory=list)


def derive_parcel(data: dict) -> dict:
    """Computed area, side lengths and the declared/computed discrepancy report."""
    derived = ParcelDerived(declared_area_m2=data.get("declared_area_m2"))
    shape = data.get("shape")
    vertices = data.get("vertices", [])
    if len(vertices) >= 3:
        points = _points(vertices)
        derived.computed_side_lengths_m = [
            round(math.dist(a, b), 3) for a, b in zip(points, points[1:] + points[:1], strict=True)
        ]
    if shape == "rectangular" and "width_m" in data and "depth_m" in data:
        derived.area_source = "width_x_depth"
        derived.computed_area_m2 = round(data["width_m"] * data["depth_m"], 2)
    elif shape in ("polygon", "irregular") and len(vertices) >= 3:
        derived.area_source = "vertices"
        derived.computed_area_m2 = round(polygon_area(_points(vertices)), 2)

    computed, declared = derived.computed_area_m2, derived.declared_area_m2
    if computed is None:
        derived.status = "not_computable"
    elif declared is None:
        derived.status = "no_declared_area"
    else:
        derived.difference_m2 = round(computed - declared, 2)
        derived.difference_percent = round(abs(computed - declared) / declared * 100, 2)
        within = derived.difference_percent <= AREA_TOLERANCE_PERCENT
        derived.status = "match" if within else "discrepancy"
    return {
        "area_source": derived.area_source,
        "computed_area_m2": derived.computed_area_m2,
        "declared_area_m2": derived.declared_area_m2,
        "difference_m2": derived.difference_m2,
        "difference_percent": derived.difference_percent,
        "status": derived.status,
        "tolerance_percent": derived.tolerance_percent,
        "computed_side_lengths_m": derived.computed_side_lengths_m,
    }
