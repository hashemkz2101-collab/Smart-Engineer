"""Conceptual layout alternatives from a buildable envelope and a space schedule (ARCH-002).

Deterministic and explainable; no HTTP or database. Each alternative is a set of
axis-aligned *space blocks* inside the buildable envelope, not walls, doors, windows or
a plan. Nothing is invented: a space without a usable area is reported as unplaced
(never dropped), outdoor spaces and parking are not modelled, and every alternative
states the criteria it applied and the criteria it did not evaluate. Missing inputs
produce a specific infeasibility result instead of a guess.
"""

import math
from collections.abc import Callable
from typing import Any

from shapely import LineString, MultiPolygon, Point, Polygon, box
from shapely import prepare as prepare_geometry
from shapely.ops import unary_union

LAYOUT_VERSION = "layout-0.1.0"
MAX_SPACES = 120
MAX_FLOORS = 20
EPS = 1e-9
ASPECTS = (1.0, 1.5, 1 / 1.5, 2.0, 0.5)
OUTDOOR_KINDS = frozenset({"yard", "terrace", "balcony", "roof_garden", "green_space"})
PRIVACY_ORDER = {
    "reception": 0,
    "living": 0,
    "kitchen": 1,
    "office": 1,
    "special": 1,
    "other": 1,
    "laundry": 2,
    "storage": 2,
    "bathroom": 2,
    "wc": 2,
    "bedroom": 3,
    "master_bedroom": 3,
}
NOT_EVALUATED = (
    "orientation_and_daylight",
    "views_and_privacy_between_buildings",
    "adjacency_and_circulation",
    "structure_and_stacking",
    "stairs_elevators_and_egress",
    "regulation_compliance",
)
LIMITATIONS = (
    "conceptual_blocks_not_a_plan",
    "net_room_areas_only",
    "same_envelope_on_every_floor",
    "not_an_approved_design",
)


class Region:
    """The buildable area (union of envelope pieces) with the few queries layout needs."""

    def __init__(self, polygons: list[dict], front_segments: list[tuple]) -> None:
        shapes = [
            Polygon(piece["exterior"], [hole for hole in piece.get("holes", [])])
            for piece in polygons
        ]
        self.shape = shapes[0] if len(shapes) == 1 else MultiPolygon(shapes)
        self.tolerant = self.shape.buffer(1e-6)
        prepare_geometry(self.tolerant)
        self.bounds = self.shape.bounds
        self.area = self.shape.area
        self.vertices = [
            tuple(point)
            for piece in polygons
            for ring in [piece["exterior"], *piece.get("holes", [])]
            for point in ring
        ]
        self.front = (
            unary_union([_line(a, b) for a, b in front_segments]) if front_segments else None
        )

    def contains_box(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        return bool(self.tolerant.contains(box(x1, y1, x2, y2)))

    def distance_to_front(self, x: float, y: float) -> float | None:
        if self.front is None:
            return None
        return float(self.front.distance(Point(x, y)))


def _line(a, b):
    return LineString([a, b])


def _area_of(space: dict) -> tuple[float | None, str]:
    if "target_area_m2" in space:
        return space["target_area_m2"], "target"
    if "area_min_m2" in space and "area_max_m2" in space:
        return (space["area_min_m2"] + space["area_max_m2"]) / 2, "range_midpoint"
    return None, "none"


def _classify(schedule_spaces: list[dict]) -> tuple[list[dict], list[dict]]:
    items: list[dict] = []
    unplaced: list[dict] = []
    for space in schedule_spaces:
        base = {"space_id": space["id"], "kind": space["kind"]}
        if space["kind"] in OUTDOOR_KINDS:
            unplaced.append({**base, "reason": "outdoor_space_not_modelled"})
        elif space["kind"] == "parking":
            unplaced.append({**base, "reason": "parking_not_modelled"})
        else:
            area, basis = _area_of(space)
            if area is None:
                has_bound = "area_min_m2" in space or "area_max_m2" in space
                reason = "area_range_incomplete" if has_bound else "area_not_given"
                unplaced.append({**base, "reason": reason})
            else:
                items.append({**base, "area": area, "basis": basis})
    return items, unplaced


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS


def _shapes(area: float) -> list[tuple[float, float]]:
    out = []
    for aspect in ASPECTS:
        width = math.sqrt(area * aspect)
        out.append((width, area / width))
    return out


def _grid(bounds: tuple) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = bounds
    step = max(1.0, max(x1 - x0, y1 - y0) / 20)
    xs = [x0 + i * step for i in range(int((x1 - x0) / step) + 1)]
    ys = [y0 + j * step for j in range(int((y1 - y0) / step) + 1)]
    return [(x, y) for y in ys for x in xs]


def _pack_floor(
    region: Region,
    items: list[dict],
    cost: Callable[[tuple], tuple],
    area_cap: float | None,
) -> tuple[list[dict], list[dict]]:
    placed: list[dict] = []
    rects: list[tuple] = []
    left: list[dict] = []
    used = 0.0
    grid = _grid(region.bounds)
    for item in items:
        if area_cap is not None and used + item["area"] > area_cap + EPS:
            left.append(item)
            continue
        origins = {*region.vertices, *grid}
        for r in rects:
            origins.update({(r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3])})
        candidates: list[tuple] = []
        for w, h in _shapes(item["area"]):
            for px, py in sorted(origins):
                for rect in (
                    (px, py, px + w, py + h),
                    (px - w, py, px, py + h),
                    (px, py - h, px + w, py),
                    (px - w, py - h, px, py),
                ):
                    if not any(_overlaps(rect, other) for other in rects):
                        candidates.append(rect)
        candidates.sort(key=lambda rect: (*cost(rect), rect))
        chosen = next((rect for rect in candidates if region.contains_box(*rect)), None)
        if chosen is None:
            left.append(item)
            continue
        rects.append(chosen)
        used += item["area"]
        placed.append(
            {
                "space_id": item["space_id"],
                "kind": item["kind"],
                "x": chosen[0],
                "y": chosen[1],
                "width": chosen[2] - chosen[0],
                "height": chosen[3] - chosen[1],
                "area_m2": item["area"],
                "area_basis": item["basis"],
            }
        )
    return placed, left


def _strategies(region: Region) -> list[dict]:
    x0, y0, x1, y1 = region.bounds
    front_known = region.front is not None

    def privacy_cost(rect: tuple) -> tuple:
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        near = region.distance_to_front(cx, cy) if front_known else cy - y0
        return (round(near, 6), cy, cx)

    return [
        {
            "key": "privacy_bands",
            "order": lambda i: (PRIVACY_ORDER.get(i["kind"], 1), -i["area"], i["space_id"]),
            "cost": privacy_cost,
            "criteria": ["public_rooms_nearest_the_front", "private_rooms_farthest_from_the_front"],
            "assumptions": [] if front_known else ["front_edge_not_identified_lowest_y_used"],
        },
        {
            "key": "largest_first_compact",
            "order": lambda i: (-i["area"], i["space_id"]),
            "cost": lambda r: (round((r[0] - x0) + (r[1] - y0), 6), r[1], r[0]),
            "criteria": ["largest_spaces_first", "compact_from_the_lower_left_corner"],
            "assumptions": [],
        },
        {
            "key": "largest_first_mirrored",
            "order": lambda i: (-i["area"], i["space_id"]),
            "cost": lambda r: (round((x1 - r[2]) + (y1 - r[3]), 6), -r[3], -r[2]),
            "criteria": ["largest_spaces_first", "compact_from_the_upper_right_corner"],
            "assumptions": [],
        },
    ]


def _signature(alternative: dict) -> tuple:
    return tuple(
        sorted(
            (p["space_id"], floor["floor"], round(p["x"], 3), round(p["y"], 3),
             round(p["width"], 3), round(p["height"], 3))
            for floor in alternative["floors"]
            for p in floor["placements"]
        )
    )


def infeasible(reasons: list[str], **details: Any) -> dict[str, Any]:
    return {
        "status": "infeasible",
        "engine_version": LAYOUT_VERSION,
        "reasons": sorted(set(reasons)),
        "details": details,
        "alternatives": [],
    }


def generate_alternatives(
    envelope: dict[str, Any],
    schedule_spaces: list[dict],
    floors_count: int,
    front_segments: list[tuple],
) -> dict[str, Any]:
    if envelope.get("status") != "computed" or not envelope.get("polygons"):
        reason = "envelope_empty" if envelope.get("status") == "empty" else "envelope_not_computed"
        return infeasible([reason, *envelope.get("reasons", [])])
    if not schedule_spaces:
        return infeasible(["no_spaces_in_schedule"])
    if len(schedule_spaces) > MAX_SPACES:
        return infeasible(["too_many_spaces_for_conceptual_layout"], limit=MAX_SPACES)
    floors_count = min(max(int(floors_count), 1), MAX_FLOORS)

    items, unplaced_fixed = _classify(schedule_spaces)
    if not items:
        return infeasible(["no_placeable_spaces"], unplaced=len(unplaced_fixed))
    region = Region(envelope["polygons"], front_segments)
    cap = envelope.get("max_footprint_m2")
    floor_capacity = min(region.area, cap) if cap is not None else region.area
    required = sum(i["area"] for i in items)
    if required > floors_count * floor_capacity + EPS:
        return infeasible(
            ["required_area_exceeds_capacity"],
            required_area_m2=required,
            capacity_m2=floors_count * floor_capacity,
            floors=floors_count,
            per_floor_capacity_m2=floor_capacity,
        )

    alternatives: list[dict] = []
    seen: set[tuple] = set()
    for strategy in _strategies(region):
        remaining = sorted(items, key=strategy["order"])
        floors: list[dict] = []
        for number in range(1, floors_count + 1):
            if not remaining:
                break
            placed, remaining = _pack_floor(region, remaining, strategy["cost"], cap)
            if not placed:
                break
            floors.append(
                {
                    "floor": number,
                    "placements": placed,
                    "used_area_m2": sum(p["area_m2"] for p in placed),
                }
            )
        unplaced = [*unplaced_fixed, *(
            {"space_id": i["space_id"], "kind": i["kind"], "reason": "did_not_fit"}
            for i in remaining
        )]
        alternative = {
            "id": f"ALT-{len(alternatives) + 1}",
            "strategy": strategy["key"],
            "criteria": strategy["criteria"],
            "assumptions": strategy["assumptions"],
            "not_evaluated": list(NOT_EVALUATED),
            "limitations": list(LIMITATIONS),
            "floors": floors,
            "unplaced": sorted(unplaced, key=lambda u: u["space_id"]),
        }
        placed_count = sum(len(f["placements"]) for f in floors)
        alternative["metrics"] = {
            "placed_spaces": placed_count,
            "unplaced_spaces": len(unplaced),
            "placed_area_m2": sum(f["used_area_m2"] for f in floors),
            "fully_placed": not remaining,
            "floors_used": len(floors),
        }
        signature = _signature(alternative)
        if placed_count and signature not in seen:
            seen.add(signature)
            alternatives.append(alternative)

    base = {
        "engine_version": LAYOUT_VERSION,
        "envelope_area_m2": region.area,
        "per_floor_capacity_m2": floor_capacity,
        "floors": floors_count,
        "total_spaces": len(schedule_spaces),
    }
    if len(alternatives) < 2:
        result = infeasible(["fewer_than_two_distinct_alternatives"], **base)
        result["alternatives"] = alternatives
        return result
    return {"status": "alternatives", "reasons": [], "details": base,
            "engine_version": LAYOUT_VERSION, "alternatives": alternatives}
