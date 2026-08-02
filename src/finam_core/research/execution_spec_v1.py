from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


SPEC_VERSION = "EXECUTION_SPEC_V1"
REQUIRED_PROFILE_FIELDS = (
    "candidate_code", "entry_mode", "stop_atr", "take_atr",
    "trail_after_r", "trail_atr",
)


def _number(value: Any) -> str | None:
    if value is None:
        return None
    return format(float(value), ".12g")


def build_execution_spec(*, symbol: str, strategy: str, side: str, timeframe: str,
                         profile: Mapping[str, Any], policy_code: str,
                         feature_schema: str = "ENTRY_CONTEXT_V1",
                         cost_model: str = "UNIFIED_COST_MODEL_REQUIRED",
                         exit_policy: str = "ENTRY_EXIT_OPTIMIZER_V1") -> dict[str, Any]:
    missing = [key for key in REQUIRED_PROFILE_FIELDS if key not in profile]
    if missing:
        raise ValueError("execution spec profile missing: " + ",".join(missing))
    return {
        "spec_version": SPEC_VERSION,
        "identity": {
            "symbol": str(symbol), "strategy": str(strategy),
            "side": str(side).upper(), "timeframe": str(timeframe).upper(),
            "candidate_code": str(profile["candidate_code"]),
        },
        "features": {"schema": feature_schema, "missing_policy": "FAIL_CLOSED"},
        "entry": {"mode": str(profile["entry_mode"]), "policy_code": str(policy_code)},
        "risk": {
            "stop_atr": _number(profile["stop_atr"]),
            "take_atr": _number(profile["take_atr"]),
            "trail_after_r": _number(profile["trail_after_r"]),
            "trail_atr": _number(profile["trail_atr"]),
        },
        "cost_model": cost_model,
        "exit_policy": exit_policy,
    }


def canonical_json(spec: Mapping[str, Any]) -> str:
    return json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def execution_spec_hash(spec: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(spec).encode("utf-8")).hexdigest()


def compare_specs(research: Mapping[str, Any], runtime: Mapping[str, Any]) -> tuple[str, list[str]]:
    if not research or not runtime:
        return "NOT_PROVEN", ["SPEC_MISSING"]
    if execution_spec_hash(research) == execution_spec_hash(runtime):
        return "MATCH", []
    keys = sorted(set(research) | set(runtime))
    return "MISMATCH", [key for key in keys if research.get(key) != runtime.get(key)]
