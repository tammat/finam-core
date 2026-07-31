from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketShockGateDecisionV1:
    allowed: bool
    state: str
    mode: str
    reason: str


def decide_market_shock_gate_v1(
    *,
    intent_type: str,
    risk_level: str,
    completed_m15_bars: int,
    gap_atr: float | None,
    spread_atr: float | None,
    relative_volume: float | None,
    market_context_fresh: bool,
    required_recovery_bars: int = 4,
    maximum_gap_atr: float = 1.5,
    maximum_spread_atr: float = 0.10,
    minimum_relative_volume: float = 0.70,
) -> MarketShockGateDecisionV1:
    """Convert external uncertainty into entry admission, never a trade signal."""
    if str(intent_type or "ENTRY").upper() == "EXIT":
        return MarketShockGateDecisionV1(True, "PROTECTIVE_EXIT", "PAPER_ALLOWED", "EXIT_ALWAYS_ALLOWED")
    level = str(risk_level or "NORMAL").upper()
    if level == "NORMAL":
        return MarketShockGateDecisionV1(True, "NORMAL", "PAPER_ALLOWED", "NO_ACTIVE_MARKET_SHOCK")
    if level in {"SHOCK", "ELEVATED"}:
        return MarketShockGateDecisionV1(False, level, "SHADOW_ONLY", f"ACTIVE_EVENT_{level}")
    if level != "RECOVERY":
        return MarketShockGateDecisionV1(False, "UNKNOWN", "BLOCK", "UNKNOWN_EVENT_RISK_LEVEL")
    checks = (
        (completed_m15_bars >= max(1, int(required_recovery_bars)), "RECOVERY_M15_INSUFFICIENT"),
        (market_context_fresh, "RECOVERY_MARKET_CONTEXT_STALE"),
        (gap_atr is not None and gap_atr <= maximum_gap_atr, "RECOVERY_GAP_TOO_LARGE_OR_UNKNOWN"),
        (spread_atr is not None and spread_atr <= maximum_spread_atr, "RECOVERY_SPREAD_TOO_WIDE_OR_UNKNOWN"),
        (relative_volume is not None and relative_volume >= minimum_relative_volume, "RECOVERY_VOLUME_TOO_LOW_OR_UNKNOWN"),
    )
    for passed, reason in checks:
        if not passed:
            return MarketShockGateDecisionV1(False, "RECOVERY", "SHADOW_ONLY", reason)
    return MarketShockGateDecisionV1(True, "RECOVERY", "PAPER_ALLOWED", "RECOVERY_CONFIRMED")
