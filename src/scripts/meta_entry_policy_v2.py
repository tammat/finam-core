from __future__ import annotations

from typing import Any, Sequence


def asset_class(symbol: str) -> str:
    if str(symbol).endswith("@MISX"):
        return "EQUITY"
    if str(symbol).endswith("@RTSX"):
        return "FUTURES"
    return "OTHER"


def load_meta_entry_policy_v2(cursor: Any, symbol: str, timeframe: str, bars: Sequence[Any]) -> dict:
    cursor.execute(
        """SELECT entry_policy FROM analytics.research_entry_profile_v2
           WHERE asset_class=%s AND timeframe=%s AND enabled
           ORDER BY updated_at DESC LIMIT 1""",
        (asset_class(symbol), timeframe),
    )
    row = cursor.fetchone() or {}
    policy = dict(row.get("entry_policy") or {})
    observed = sum(1 for bar in bars if float(getattr(bar, "volume", 0.0) or 0.0) > 0)
    coverage = observed / len(bars) if bars else 0.0
    policy["entry_volume_coverage"] = round(coverage, 6)
    if coverage < float(policy.get("entry_min_volume_coverage", 0.80)):
        policy["entry_volume_mode"] = "OBSERVE"
    return policy


def apply_meta_entry_policy_v2(params: dict, policy: dict) -> dict:
    if str(params.get("entry_policy_code", "NONE")) != "META_ENTRY_V2":
        return params
    return {**params, **policy, "entry_policy_code": "META_ENTRY_V2"}
