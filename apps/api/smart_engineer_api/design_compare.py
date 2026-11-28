"""Comparing two design model snapshots by stable element ID (ARCH-006). Pure, no database."""

from typing import Any


def _by_id(model: dict[str, Any]) -> dict[str, dict]:
    return {element["id"]: element for element in model.get("elements", [])}


def compare_models(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """What changed going from ``first`` to ``second``.

    Elements are matched by their stable ID. ``changed`` lists every field that differs
    (a field that appears or disappears has ``None`` on the missing side).
    """
    before, after = _by_id(first), _by_id(second)
    removed = [before[i] for i in before if i not in after]
    added = [after[i] for i in after if i not in before]
    changed = []
    unchanged = 0
    for element_id in before:
        if element_id not in after:
            continue
        old, new = before[element_id], after[element_id]
        fields = [
            {"field": key, "before": old.get(key), "after": new.get(key)}
            for key in sorted(set(old) | set(new))
            if old.get(key) != new.get(key)
        ]
        if fields:
            changed.append(
                {"id": element_id, "type": new["type"], "floor": new["floor"], "fields": fields}
            )
        else:
            unchanged += 1
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "summary": {"added": len(added), "removed": len(removed), "changed": len(changed)},
    }
