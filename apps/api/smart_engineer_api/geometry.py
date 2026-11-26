"""Deterministic local-plane parcel geometry (GEOM-001/002/003).

No HTTP, database, UI, or regulatory authority. Setback distances mean Euclidean
clearance from each explicitly assigned boundary segment. Round joins are
conservatively approximated with a bounded chord error, never a convex hull.
"""

import copy
import hashlib
import json
import math
from datetime import UTC, date, datetime

from shapely import LinearRing, LineString, Polygon, union_all
from shapely.errors import GEOSException
from shapely.validation import explain_validity

ENGINE_VERSION = "local-plane-1.0.0/shapely-2.2.0"
LENGTH_EPS_M = 1e-7
AREA_EPS_M2 = 1e-8
ARC_ERROR_M = 0.001  # conservative over-clearance, at most 1 mm per circular exclusion
MAX_VERTICES = 200
MAX_COORD_M = 1e7
UNIT_FACTORS = {"m": 1.0, "cm": 0.01, "mm": 0.001}
EDGE_ROLES = ("front", "rear", "left", "right")
DISCLAIMER = "محاسبهٔ اولیه بر اساس دادهٔ واردشده؛ نه تأیید قانونی، نقشه‌برداری رسمی یا مجوز ساخت."


class GeometryError(ValueError):
    def __init__(self, code: str, field: str = "vertices") -> None:
        super().__init__(code)
        self.code = code
        self.field = field


def number(value, field: str) -> float:
    if isinstance(value, bool):
        raise GeometryError("not_a_number", field)
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        raise GeometryError("not_a_number", field) from None
    if not math.isfinite(result):
        raise GeometryError("not_a_number", field)
    return result


def canonicalize(data: dict, unit: str = "m") -> dict:
    """Only editable boundary coordinates/dimensions use `unit`; area stays m².

    Survey points and manually recorded side lengths retain their existing metre
    contract. `coordinate_system` remains a descriptive survey reference, not an
    instruction to project latitude/longitude or EPSG coordinates.
    """
    if unit not in UNIT_FACTORS:
        raise GeometryError("unsupported_unit", "unit")
    if (data.get("geometry_reference") or "local_cartesian") != "local_cartesian":
        raise GeometryError("unsupported_reference", "geometry_reference")
    out = copy.deepcopy(data)
    scale = UNIT_FACTORS[unit]
    for name in ("width_m", "depth_m"):
        if out.get(name) not in (None, ""):
            out[name] = number(out[name], name) * scale
    if "vertices" in out:
        if not isinstance(out["vertices"], list) or len(out["vertices"]) > MAX_VERTICES:
            raise GeometryError("too_many_items")
        for i, vertex in enumerate(out["vertices"]):
            if not isinstance(vertex, dict):
                raise GeometryError("not_an_object", f"vertices[{i}]")
            for axis in ("x", "y"):
                vertex[axis] = number(vertex.get(axis), f"vertices[{i}].{axis}") * scale
    out["geometry_reference"] = "local_cartesian"
    return out


def polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    # Translate before summing to avoid cancellation on large survey coordinates.
    x0, y0 = points[0]
    local = [(x - x0, y - y0) for x, y in points]
    return abs(math.fsum(
        a[0] * b[1] - b[0] * a[1]
        for a, b in zip(local, local[1:] + local[:1], strict=True)
    )) / 2


def is_simple_polygon(points: list[tuple[float, float]]) -> bool:
    return len(points) >= 3 and bool(LinearRing(points).is_simple)


def boundary(data: dict) -> list[tuple[float, float]]:
    shape = data.get("shape")
    if shape == "rectangular":
        w, h = (number(data.get(k), k) for k in ("width_m", "depth_m"))
        if not (0.01 <= w <= 100000 and 0.01 <= h <= 100000):
            raise GeometryError("out_of_range", "width_m")
        points = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    elif shape in ("polygon", "irregular"):
        vertices = data.get("vertices", [])
        if not isinstance(vertices, list) or len(vertices) < 3:
            raise GeometryError("too_few_points")
        if len(vertices) > MAX_VERTICES:
            raise GeometryError("too_many_items")
        points = []
        for i, vertex in enumerate(vertices):
            if not isinstance(vertex, dict):
                raise GeometryError("not_an_object", f"vertices[{i}]")
            points.append(tuple(number(vertex.get(a), f"vertices[{i}].{a}") for a in ("x", "y")))
    else:
        raise GeometryError("required", "shape")
    validate_boundary(points)
    return points


def validate_boundary(points: list[tuple[float, float]]) -> None:
    if any(not math.isfinite(v) or abs(v) > MAX_COORD_M for p in points for v in p):
        raise GeometryError("out_of_range")
    if len(set(points)) != len(points):
        raise GeometryError("duplicate_vertex")
    for a, b in zip(points, points[1:] + points[:1], strict=True):
        if math.dist(a, b) <= LENGTH_EPS_M:
            raise GeometryError("zero_length_edge")
    if polygon_area(points) <= AREA_EPS_M2:
        raise GeometryError("degenerate")
    polygon = Polygon(points)
    if not polygon.is_valid:
        reason = explain_validity(polygon)
        code = "self_intersecting" if "intersection" in reason.lower() else "invalid_geometry"
        raise GeometryError(code)
    if polygon.minimum_clearance <= LENGTH_EPS_M:
        raise GeometryError("precision_insufficient")


def fingerprint(value) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def analyze(data: dict, access: dict | None = None) -> dict:
    if (data.get("geometry_reference") or "local_cartesian") != "local_cartesian":
        raise GeometryError("unsupported_reference", "geometry_reference")
    points = boundary(data)
    polygon = Polygon(points)
    access = access or {}
    north = access.get("north_angle_deg")
    north = number(north, "north_angle_deg") if north is not None else None
    if north is not None and not 0 <= north <= 360:
        raise GeometryError("out_of_range", "north_angle_deg")
    edges = []
    for i, (a, b) in enumerate(zip(points, points[1:] + points[:1], strict=True)):
        local_bearing = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360
        edges.append({
            "index": i, "length_m": math.dist(a, b),
            "local_bearing_deg": local_bearing,
            "north_bearing_deg": (local_bearing - north) % 360 if north is not None else None,
        })
    area = polygon_area(points)
    declared = data.get("declared_area_m2")
    declared = number(declared, "declared_area_m2") if declared not in (None, "") else None
    if declared is not None and declared <= 0:
        raise GeometryError("out_of_range", "declared_area_m2")
    difference = area - declared if declared is not None else None
    percent = abs(difference) / declared * 100 if declared is not None else None
    return {
        "status": "valid", "engine_version": ENGINE_VERSION,
        "reference": "local_cartesian", "unit": "m", "area_unit": "m2",
        "axes": {"x": "right", "y": "up"},
        "vertices": [{"x": x, "y": y} for x, y in points],
        "area_m2": area, "perimeter_m": polygon.length,
        "edges": edges, "bounds_m": list(polygon.bounds),
        "orientation": "counterclockwise" if polygon.exterior.is_ccw else "clockwise",
        "north_angle_deg": north, "access_fronts": access.get("access_fronts"),
        "declared_area_m2": declared, "difference_m2": difference,
        "difference_percent": percent,
        "area_status": "no_declared_area" if percent is None else (
            "match" if percent <= 1.0 else "discrepancy"
        ),
        "input_hash": fingerprint(data),
        "tolerances": {"length_m": LENGTH_EPS_M, "area_m2": AREA_EPS_M2,
                       "area_discrepancy_percent": 1.0, "setback_arc_error_m": ARC_ERROR_M,
                       "status": "development_defaults_not_survey_approval"},
        "warnings": [] if north is not None else ["north_not_provided"],
        "disclaimer": DISCLAIMER,
    }


def source_problems(data: dict, today: date) -> list[str]:
    missing = [name for name in ("source_type", "source_date", "source_calendar", "source_revision",
                                 "valid_from", "valid_until") if not data.get(name)]
    if not (data.get("source_title") or data.get("source_reference")):
        missing.append("source_title_or_reference")
    if data.get("source_verified") is not True:
        missing.append("source_not_verified")
    try:
        start, end = date.fromisoformat(data["valid_from"]), date.fromisoformat(data["valid_until"])
        if start > end:
            missing.append("validity_inverted")
        elif today < start:
            missing.append("source_not_yet_valid")
        elif today > end:
            missing.append("source_expired")
    except (ValueError, KeyError, TypeError):
        if data.get("valid_from") and data.get("valid_until"):
            missing.append("invalid_validity")
    return missing


def buildable_envelope(
    data: dict, setbacks: dict, coverage: dict | None = None, *, today: date | None = None,
) -> dict:
    today = today or datetime.now(UTC).date()
    points = boundary(data)
    problems = source_problems(setbacks, today)
    mapping = data.get("setback_edges", [])
    assigned: dict[int, str] = {}
    if not isinstance(mapping, list):
        problems.append("edge_mapping_required")
    else:
        for item in mapping:
            index, role = item.get("edge_index"), item.get("role")
            if (isinstance(index, bool) or not isinstance(index, int) or index in assigned
                    or not 0 <= index < len(points) or role not in EDGE_ROLES):
                problems.append("invalid_edge_mapping")
            else:
                assigned[index] = role
    if len(assigned) != len(points):
        problems.append("edge_mapping_required")
    for role in set(assigned.values()):
        if setbacks.get(f"{role}_m") is None:
            problems.append(f"{role}_m_required")
    if setbacks.get("correction_notes", "").strip():
        problems.append("correction_needs_human_review")
    if problems:
        return {"status": "needs_inquiry", "reasons": sorted(set(problems)), "polygons": [],
                "area_m2": None, "max_footprint_m2": None}
    try:
        original = Polygon(points)
        exclusions = []
        for i, (a, b) in enumerate(zip(points, points[1:] + points[:1], strict=True)):
            distance = number(setbacks[f"{assigned[i]}_m"], f"{assigned[i]}_m")
            if not 0 <= distance <= 1000:
                raise GeometryError("out_of_range", "setbacks")
            if distance == 0:
                continue
            # Circumscribe, rather than inscribe, the clearance circle. The result
            # cannot claim buildable space inside the required exclusion distance.
            q = max(8, math.ceil(math.pi / (4 * math.acos(distance / (distance + ARC_ERROR_M)))))
            radius = distance / math.cos(math.pi / (4 * q))
            exclusions.append(LineString([a, b]).buffer(radius, quad_segs=q))
        result = original.difference(union_all(exclusions)) if exclusions else original
        pieces = [] if result.is_empty else (
            [result] if result.geom_type == "Polygon" else list(result.geoms)
        )
        polygons = []
        for piece in sorted(pieces, key=lambda p: (-p.area, p.bounds)):
            if piece.geom_type != "Polygon" or piece.area <= AREA_EPS_M2:
                continue
            polygons.append({
                "exterior": [list(p) for p in list(piece.exterior.coords)[:-1]],
                "holes": [[list(p) for p in list(ring.coords)[:-1]] for ring in piece.interiors],
                "area_m2": piece.area,
            })
        limit = None
        coverage_reasons = source_problems(coverage or {}, today)
        if not coverage_reasons and (coverage or {}).get("max_coverage_percent") is not None:
            percent = number(coverage["max_coverage_percent"], "max_coverage_percent")
            if 0 <= percent <= 100:
                limit = min(result.area, original.area * percent / 100)
        return {
            "status": "empty" if not polygons else "computed", "reasons": [],
            "polygons": polygons, "area_m2": sum(p["area_m2"] for p in polygons),
            "max_footprint_m2": limit,
            "coverage_status": "verified_input" if limit is not None else "needs_inquiry",
            "clearance_method": "euclidean_segment_clearance_conservative_round_joins",
            "max_arc_overclearance_m": ARC_ERROR_M, "as_of": today.isoformat(),
        }
    except GEOSException:
        return {"status": "needs_inquiry", "reasons": ["precision_insufficient"],
                "polygons": [], "area_m2": None, "max_footprint_m2": None}
