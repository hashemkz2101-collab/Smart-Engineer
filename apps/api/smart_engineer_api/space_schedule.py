"""Deterministic space schedule built from the saved program (ARCH-001).

Pure functions, no database. The same program always yields the same schedule.
Nothing is invented: an omitted count is listed as one space and flagged, an omitted
area stays omitted and is flagged, and no figure is multiplied by the number of units
(the program does not say whether room counts are per unit). Totals are *net room
areas only*; walls, circulation and structure are not included, so they are never
presented as a building area.
"""

from typing import Any

LIMITATIONS = (
    "net_room_areas_only",
    "counts_as_listed_not_multiplied_by_units",
    "no_layout_or_geometry",
)


def _flag(code: str, severity: str, room_index: int | None = None) -> dict[str, Any]:
    flag: dict[str, Any] = {"code": code, "severity": severity}
    if room_index is not None:
        flag["room_index"] = room_index
    return flag


def _round(value: float) -> float:
    return round(value, 6)


def build_schedule(program: dict[str, Any], program_version: int) -> dict[str, Any]:
    rooms = program.get("rooms", [])
    spaces: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []

    if not rooms:
        flags.append(_flag("no_rooms", "warning"))
    if program.get("units_count", 1) > 1:
        flags.append(_flag("multi_unit_counts_not_multiplied", "info"))
    target = program.get("target_area_m2")
    low_target, high_target = program.get("target_area_min_m2"), program.get("target_area_max_m2")
    if target is not None:
        if (low_target is not None and target < low_target) or (
            high_target is not None and target > high_target
        ):
            flags.append(_flag("program_target_outside_range", "warning"))

    lower = upper = target_sum = 0.0
    with_area = 0
    for room_index, room in enumerate(rooms):
        count = room.get("count")
        if count is None:
            flags.append(_flag("count_not_given", "info", room_index))
        count = 1 if count is None else count
        area = {
            key: room[key]
            for key in ("target_area_m2", "area_min_m2", "area_max_m2")
            if key in room
        }
        lo = room.get("area_min_m2", room.get("target_area_m2"))
        hi = room.get("area_max_m2", room.get("target_area_m2"))
        if not area:
            flags.append(_flag("area_not_given", "warning", room_index))
        else:
            point = room.get("target_area_m2")
            if point is not None and (
                ("area_min_m2" in room and point < room["area_min_m2"])
                or ("area_max_m2" in room and point > room["area_max_m2"])
            ):
                flags.append(_flag("target_outside_range", "warning", room_index))
        for ordinal in range(1, count + 1):
            space: dict[str, Any] = {
                "id": f"S-{len(spaces) + 1:03d}",
                "kind": room["kind"],
                "room_index": room_index,
                "ordinal": ordinal,
                "of": count,
                **area,
            }
            if "name" in room:
                space["name"] = room["name"]
            spaces.append(space)
            if area:
                with_area += 1
            if lo is not None:
                lower += lo
            if hi is not None:
                upper += hi
            if "target_area_m2" in room:
                target_sum += room["target_area_m2"]

    without_area = len(spaces) - with_area
    bounds_complete = bool(spaces) and without_area == 0
    if high_target is not None and lower > high_target:
        flags.append(_flag("program_exceeds_target_area", "warning"))
    if low_target is not None and bounds_complete and upper < low_target:
        flags.append(_flag("program_below_target_area", "info"))

    source = {
        key: program[key]
        for key in (
            "units_count",
            "floors_count",
            "target_area_m2",
            "target_area_min_m2",
            "target_area_max_m2",
        )
        if key in program
    }
    return {
        "source": {"program_version": program_version, **source},
        "counts_basis": "as_listed",
        "spaces": spaces,
        "totals": {
            "rooms": len(rooms),
            "spaces": len(spaces),
            "spaces_with_area": with_area,
            "spaces_without_area": without_area,
            "area_lower_m2": _round(lower),
            "area_upper_m2": _round(upper),
            "target_sum_m2": _round(target_sum),
            "bounds_complete": bounds_complete,
        },
        "flags": flags,
        "limitations": list(LIMITATIONS),
    }
