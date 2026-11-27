"""Editable base design model and its edit operations (ARCH-003).

Pure functions, no database. The model is a plain JSON document in metres on the parcel's
local plane (X right, Y up). Elements have stable IDs that are never reused. Every edit is
an explicit operation; a batch is applied atomically (the first failure rejects all of it)
and a locked element rejects every edit except unlocking, with an explicit reason.

Spaces stay axis-aligned: rotation is in multiples of 90 degrees. Walls may have any
direction. Doors, windows and openings are hosted on a wall and positioned along it.
Nothing here checks overlap, closure or regulations (that is ARCH-007/ARCH-008).
"""

import copy
import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

SCHEMA = 1
MAX_ELEMENTS = 5000
MAX_OPERATIONS = 50
MAX_COORDINATE = 100_000.0
MAX_FLOOR = 20
EPS = 1e-6
HOSTED = ("door", "window", "opening")
VERTICAL_KINDS = ("stair", "elevator", "shaft")
TYPES = ("space", "wall", "vertical", *HOSTED)
FOOTPRINTS = ("space", "vertical")


UNIT_FACTORS = {"m": Decimal(1), "cm": Decimal("0.01"), "mm": Decimal("0.001")}
LENGTH_OP_KEYS = ("dx", "dy", "along_m", "width", "height", "length_m", "width_m")
LENGTH_ELEMENT_KEYS = (
    "x", "y", "width", "height", "x1", "y1", "x2", "y2",
    "offset_m", "width_m", "thickness_m", "height_m", "sill_m",
)
SNAPPED_KEYS = ("x", "y", "width", "height", "x1", "y1", "x2", "y2", "offset_m", "width_m")
MIN_GRID_M = Decimal("0.001")
MAX_GRID_M = Decimal(100)


class DesignError(Exception):
    def __init__(self, code: str, index: int | None = None, element_id: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.index = index
        self.element_id = element_id


def empty_model(source: dict | None = None) -> dict[str, Any]:
    return {"schema": SCHEMA, "units": "m", "next_id": 1, "source": source, "elements": []}


def _number(value: Any, *, positive: bool = False, non_negative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("number")
    number = float(value)
    if not math.isfinite(number) or abs(number) > MAX_COORDINATE:
        raise ValueError("range")
    if (positive and number <= 0) or (non_negative and number < 0):
        raise ValueError("sign")
    return round(number, 6)


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("text")
    return value.strip()


def _floor(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_FLOOR:
        raise ValueError("floor")
    return value


def _floors(value: Any) -> list[int]:
    if not isinstance(value, list) or not 2 <= len(value) <= MAX_FLOOR:
        raise ValueError("floors")
    levels = sorted({_floor(item) for item in value})
    if len(levels) != len(value):
        raise ValueError("floors")
    return levels


def wall_length(wall: dict) -> float:
    return math.hypot(wall["x2"] - wall["x1"], wall["y2"] - wall["y1"])


def _find(model: dict, element_id: Any, index: int) -> dict:
    for element in model["elements"]:
        if element["id"] == element_id:
            return element
    raise DesignError("unknown_element", index, element_id if isinstance(element_id, str) else None)


def _hosted_by(model: dict, wall_id: str) -> list[dict]:
    return [e for e in model["elements"] if e["type"] in HOSTED and e.get("wall_id") == wall_id]


def _guard_locked(element: dict, index: int) -> None:
    if element.get("locked"):
        raise DesignError("element_locked", index, element["id"])


def _guard_hosted_locked(model: dict, element: dict, index: int) -> None:
    if element["type"] == "wall":
        for hosted in _hosted_by(model, element["id"]):
            if hosted.get("locked"):
                raise DesignError("hosted_element_locked", index, hosted["id"])


def _check_hosted_fits(model: dict, wall: dict, index: int) -> None:
    length = wall_length(wall)
    for hosted in _hosted_by(model, wall["id"]):
        if hosted["offset_m"] + hosted["width_m"] > length + EPS:
            raise DesignError("hosted_opening_outside_wall", index, hosted["id"])


def _build(model: dict, spec: Any, index: int) -> dict:
    if not isinstance(spec, dict) or spec.get("type") not in TYPES:
        raise DesignError("invalid_value", index)
    kind = spec["type"]
    try:
        element: dict[str, Any] = {"type": kind, "floor": _floor(spec.get("floor", 1)),
                                   "locked": False}
        if kind == "space":
            element.update(
                kind=_text(spec.get("kind"), 40),
                x=_number(spec["x"]), y=_number(spec["y"]),
                width=_number(spec["width"], positive=True),
                height=_number(spec["height"], positive=True),
                rotation_deg=0,
            )
            if spec.get("name") is not None:
                element["name"] = _text(spec["name"], 120)
            if spec.get("schedule_space_id") is not None:
                element["schedule_space_id"] = _text(spec["schedule_space_id"], 20)
        elif kind == "vertical":
            levels = _floors(spec.get("floors"))
            if spec.get("kind") not in VERTICAL_KINDS:
                raise ValueError("kind")
            element.update(
                floor=levels[0], floors=levels, kind=spec["kind"],
                x=_number(spec["x"]), y=_number(spec["y"]),
                width=_number(spec["width"], positive=True),
                height=_number(spec["height"], positive=True),
                rotation_deg=0,
            )
        elif kind == "wall":
            element.update(
                x1=_number(spec["x1"]), y1=_number(spec["y1"]),
                x2=_number(spec["x2"]), y2=_number(spec["y2"]),
                thickness_m=_number(spec["thickness_m"], positive=True),
            )
            if wall_length(element) <= EPS or element["thickness_m"] > 2:
                raise ValueError("wall")
        else:
            wall = _find(model, spec.get("wall_id"), index)
            if wall["type"] != "wall":
                raise DesignError("wrong_host_type", index, wall["id"])
            element.update(
                floor=wall["floor"], wall_id=wall["id"],
                offset_m=_number(spec["offset_m"], non_negative=True),
                width_m=_number(spec["width_m"], positive=True),
            )
            for optional in ("height_m", "sill_m"):
                if spec.get(optional) is not None:
                    element[optional] = _number(spec[optional], non_negative=optional == "sill_m",
                                                positive=optional == "height_m")
            if element["offset_m"] + element["width_m"] > wall_length(wall) + EPS:
                raise DesignError("opening_outside_wall", index, wall["id"])
        if spec.get("label") is not None:
            element["label"] = _text(spec["label"], 120)
        return element
    except (KeyError, ValueError):
        raise DesignError("invalid_value", index) from None


def _apply_one(model: dict, op: Any, index: int) -> None:
    if not isinstance(op, dict) or not isinstance(op.get("op"), str):
        raise DesignError("unknown_operation", index)
    name = op["op"]
    if name == "add":
        if len(model["elements"]) >= MAX_ELEMENTS:
            raise DesignError("too_many_elements", index)
        element = _build(model, op.get("element"), index)
        element["id"] = f"E-{model['next_id']:04d}"
        model["next_id"] += 1
        model["elements"].append({"id": element.pop("id"), **element})
        return
    if name == "copy_floor":
        _copy_floor(model, op, index)
        return
    if name not in ("move", "resize", "rotate", "delete", "lock", "unlock", "set", "set_floors"):
        raise DesignError("unknown_operation", index)
    element = _find(model, op.get("id"), index)
    eid = element["id"]
    if name == "unlock":
        element["locked"] = False
        return
    if name == "lock":
        element["locked"] = True
        return
    _guard_locked(element, index)
    kind = element["type"]
    try:
        if name == "delete":
            _guard_hosted_locked(model, element, index)
            doomed = {eid, *(h["id"] for h in _hosted_by(model, eid))}
            model["elements"] = [e for e in model["elements"] if e["id"] not in doomed]
        elif name == "move":
            if kind in HOSTED:
                wall = _find(model, element["wall_id"], index)
                offset = round(element["offset_m"] + _number(op["along_m"]), 6)
                if offset < -EPS or offset + element["width_m"] > wall_length(wall) + EPS:
                    raise DesignError("opening_outside_wall", index, eid)
                element["offset_m"] = max(offset, 0.0)
            else:
                _guard_hosted_locked(model, element, index)
                dx, dy = _number(op["dx"]), _number(op["dy"])
                keys = ("x1", "x2") if kind == "wall" else ("x",)
                for key in keys:
                    element[key] = round(element[key] + dx, 6)
                for key in ("y1", "y2") if kind == "wall" else ("y",):
                    element[key] = round(element[key] + dy, 6)
        elif name == "resize":
            if kind in FOOTPRINTS:
                element["width"] = _number(op["width"], positive=True)
                element["height"] = _number(op["height"], positive=True)
            elif kind == "wall":
                _guard_hosted_locked(model, element, index)
                length = _number(op["length_m"], positive=True)
                old = wall_length(element)
                scale = length / old
                element["x2"] = round(element["x1"] + (element["x2"] - element["x1"]) * scale, 6)
                element["y2"] = round(element["y1"] + (element["y2"] - element["y1"]) * scale, 6)
                _check_hosted_fits(model, element, index)
            else:
                wall = _find(model, element["wall_id"], index)
                width = _number(op["width_m"], positive=True)
                if element["offset_m"] + width > wall_length(wall) + EPS:
                    raise DesignError("opening_outside_wall", index, eid)
                element["width_m"] = width
        elif name == "rotate":
            degrees = _number(op["degrees"])
            if kind in HOSTED:
                raise DesignError("operation_not_supported", index, eid)
            if kind in FOOTPRINTS:
                if degrees % 90 != 0:
                    raise DesignError("rotation_must_be_multiple_of_90", index, eid)
                turns = int(degrees // 90) % 4
                cx, cy = element["x"] + element["width"] / 2, element["y"] + element["height"] / 2
                if turns % 2:
                    element["width"], element["height"] = element["height"], element["width"]
                    element["x"] = round(cx - element["width"] / 2, 6)
                    element["y"] = round(cy - element["height"] / 2, 6)
                element["rotation_deg"] = (element["rotation_deg"] + turns * 90) % 360
            else:
                _guard_hosted_locked(model, element, index)
                cx, cy = (element["x1"] + element["x2"]) / 2, (element["y1"] + element["y2"]) / 2
                angle = math.radians(degrees)
                for sx, sy in (("x1", "y1"), ("x2", "y2")):
                    rx, ry = element[sx] - cx, element[sy] - cy
                    element[sx] = round(cx + rx * math.cos(angle) - ry * math.sin(angle), 6)
                    element[sy] = round(cy + rx * math.sin(angle) + ry * math.cos(angle), 6)
        elif name == "set_floors":
            if kind != "vertical":
                raise DesignError("operation_not_supported", index, eid)
            element["floors"] = _floors(op["floors"])
            element["floor"] = element["floors"][0]
        else:  # set
            fields = op.get("fields")
            allowed = {
                "space": {"kind": 40, "name": 120, "label": 120},
                "wall": {"label": 120},
                "vertical": {"label": 120, "name": 120},
                "door": {"label": 120}, "window": {"label": 120}, "opening": {"label": 120},
            }[kind]
            if not isinstance(fields, dict) or not fields or set(fields) - set(allowed):
                raise DesignError("invalid_value", index, eid)
            for key, value in fields.items():
                element[key] = _text(value, allowed[key])
    except (KeyError, ValueError, ZeroDivisionError):
        raise DesignError("invalid_value", index, eid) from None


def _copy_floor(model: dict, op: dict, index: int) -> None:
    """Repeat every non-vertical element of one floor onto empty floors, with new stable IDs."""
    try:
        source = _floor(op["from_floor"])
        targets = op["to_floors"]
        if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_FLOOR:
            raise ValueError("to_floors")
        targets = [_floor(item) for item in targets]
        if len(set(targets)) != len(targets) or source in targets:
            raise ValueError("to_floors")
    except (KeyError, ValueError):
        raise DesignError("invalid_value", index) from None
    originals = [e for e in model["elements"] if e["floor"] == source and e["type"] != "vertical"]
    if not originals:
        raise DesignError("unknown_floor", index)
    for target in targets:
        if any(e["floor"] == target and e["type"] != "vertical" for e in model["elements"]):
            raise DesignError("floor_not_empty", index)
    if len(model["elements"]) + len(originals) * len(targets) > MAX_ELEMENTS:
        raise DesignError("too_many_elements", index)
    for target in targets:
        mapping: dict[str, str] = {}
        for original in originals:
            mapping[original["id"]] = f"E-{model['next_id']:04d}"
            model["next_id"] += 1
        for original in originals:
            copy_ = copy.deepcopy(original)
            copy_.pop("schedule_space_id", None)  # a copy is not the scheduled space
            copy_.update(id=mapping[original["id"]], floor=target, copied_from=original["id"])
            if "wall_id" in copy_:
                copy_["wall_id"] = mapping[original["wall_id"]]
            model["elements"].append(copy_)


def validate_levels(model: dict, index: int) -> None:
    """Every vertical connection must point only at floors that actually have elements."""
    levels = {e["floor"] for e in model["elements"] if e["type"] != "vertical"}
    for element in model["elements"]:
        if element["type"] == "vertical" and not set(element["floors"]) <= levels:
            raise DesignError("vertical_invalid_level", index, element["id"])


def to_metres(value: Any, unit: str) -> Any:
    """Exact decimal conversion (150 cm -> 1.5 m); non-numbers pass through to validation."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    if unit == "m":
        return value
    try:
        return float(Decimal(str(value)) * UNIT_FACTORS[unit])
    except (InvalidOperation, ValueError):
        return value


def _convert(op: Any, unit: str) -> Any:
    if unit == "m" or not isinstance(op, dict):
        return op
    converted = dict(op)
    for key in LENGTH_OP_KEYS:
        if key in converted:
            converted[key] = to_metres(converted[key], unit)
    spec = converted.get("element")
    if isinstance(spec, dict):
        converted["element"] = {
            key: to_metres(value, unit) if key in LENGTH_ELEMENT_KEYS else value
            for key, value in spec.items()
        }
    return converted


def snap_value(value: float, grid: Decimal) -> float:
    """Nearest multiple of the grid; exact ties round away from zero."""
    scaled = Decimal(str(value)) / grid
    rounded = scaled.copy_abs().quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return round(float((rounded if scaled >= 0 else -rounded) * grid), 6)


def _grid(snap: Any, unit: str) -> Decimal | None:
    if snap is None:
        return None
    try:
        raw = snap["grid"] if isinstance(snap, dict) else None
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError
        grid = Decimal(str(raw)) * UNIT_FACTORS[snap.get("unit", unit)]
    except (KeyError, ValueError, InvalidOperation):
        raise DesignError("invalid_snap") from None
    if not MIN_GRID_M <= grid <= MAX_GRID_M:
        raise DesignError("invalid_snap")
    return grid


def _snap_touched(model: dict, touched: set[str], grid: Decimal, index: int) -> None:
    for element in model["elements"]:
        if element["id"] not in touched:
            continue
        for key in SNAPPED_KEYS:
            if key in element:
                element[key] = snap_value(element[key], grid)
        eid = element["id"]
        kind = element["type"]
        if (kind in FOOTPRINTS and (element["width"] <= 0 or element["height"] <= 0)) or (
            kind == "wall" and wall_length(element) <= EPS
        ):
            raise DesignError("snap_collapses_element", index, eid)
        if kind == "wall":
            _check_hosted_fits(model, element, index)
        if kind in HOSTED:
            wall = _find(model, element["wall_id"], index)
            if (
                element["offset_m"] < 0
                or element["width_m"] <= 0
                or element["offset_m"] + element["width_m"] > wall_length(wall) + EPS
            ):
                raise DesignError("snap_collapses_element", index, eid)


def _touched_ids(before: dict, after: dict, op: dict) -> set[str]:
    """Elements whose geometry the operation created or changed (rotation is never snapped)."""
    if op.get("op") not in ("add", "move", "resize"):
        return set()
    old = {e["id"]: e for e in before["elements"]}
    return {e["id"] for e in after["elements"] if old.get(e["id"]) != e}


def apply_operations(
    model: dict[str, Any],
    operations: Any,
    *,
    unit: str = "m",
    snap: Any = None,
) -> dict[str, Any]:
    """Return a new model with all operations applied, or raise DesignError (no partial result).

    Length values in the request are in ``unit`` (m, cm or mm) and are converted exactly.
    With ``snap``, the geometry an add/move/resize changed is rounded to the grid.
    """
    if unit not in UNIT_FACTORS:
        raise DesignError("invalid_unit")
    if not isinstance(operations, list) or not operations:
        raise DesignError("invalid_value")
    if len(operations) > MAX_OPERATIONS:
        raise DesignError("too_many_operations")
    grid = _grid(snap, unit)
    working = copy.deepcopy(model)
    for index, raw in enumerate(operations):
        op = _convert(raw, unit)
        before = copy.deepcopy(working) if grid is not None else None
        _apply_one(working, op, index)
        if grid is not None and before is not None and isinstance(op, dict):
            _snap_touched(working, _touched_ids(before, working, op), grid, index)
    validate_levels(working, len(operations) - 1)
    return working


def from_layout_alternative(alternative: dict[str, Any], source: dict) -> dict[str, Any]:
    model = empty_model(source)
    operations = [
        {
            "op": "add",
            "element": {
                "type": "space", "floor": floor["floor"], "kind": placement["kind"],
                "x": placement["x"], "y": placement["y"],
                "width": placement["width"], "height": placement["height"],
                "schedule_space_id": placement["space_id"],
            },
        }
        for floor in alternative["floors"]
        for placement in floor["placements"]
    ]
    return apply_operations(model, operations) if operations else model
