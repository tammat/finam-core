from __future__ import annotations

from math import isclose
from typing import Any, Mapping


FEATURE_KEYS = (
    "atr_percentile", "relative_volume", "regime", "cost_to_atr",
    "higher_timeframe_aligned",
)


def compare_observation(research: Mapping[str, Any], runtime: Mapping[str, Any]) -> tuple[str, list[str]]:
    mismatches: list[str] = []
    missing: list[str] = []
    for key in FEATURE_KEYS:
        left, right = research.get("features", {}).get(key), runtime.get("features", {}).get(key)
        if left is None or right is None:
            missing.append(f"feature:{key}")
        elif isinstance(left, (int, float)) or isinstance(right, (int, float)):
            if not isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-12):
                mismatches.append(f"feature:{key}")
        elif str(left) != str(right):
            mismatches.append(f"feature:{key}")
    for key in ("decision", "entry_mode", "side", "timeframe"):
        left, right = research.get(key), runtime.get(key)
        if left is None or right is None:
            missing.append(key)
        elif str(left) != str(right):
            mismatches.append(key)
    for key in ("entry_price", "quantity", "exit_price", "costs", "net_r"):
        left, right = research.get(key), runtime.get(key)
        if left is None or right is None:
            missing.append(key)
        elif not isclose(float(left), float(right), rel_tol=1e-7, abs_tol=1e-8):
            mismatches.append(key)
    if mismatches:
        return "MISMATCH", sorted(set(mismatches))
    if missing:
        return "NOT_PROVEN", sorted(set(missing))
    return "MATCH", []
