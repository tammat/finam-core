from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeRuntimeOverride:
    runtime_action: str
    max_position_size: float
    allowed_execution_mode: str
    risk_multiplier: float
    cooldown_sec: int
    stop_take_profile: str
    reason: str


def build_regime_runtime_override(*, recommendation: str, score: float, confidence: float) -> RegimeRuntimeOverride:
    """Русский комментарий: переводим runtime recommendation в ограничения для risk/execution."""
    rec = recommendation.upper()

    if "REGIME_BLOCK" in rec:
        return RegimeRuntimeOverride(
            runtime_action="BLOCK",
            max_position_size=0.0,
            allowed_execution_mode="blocked",
            risk_multiplier=0.0,
            cooldown_sec=3600,
            stop_take_profile="no_entry",
            reason="regime_matrix_block",
        )

    if "REGIME_ALLOW" in rec:
        return RegimeRuntimeOverride(
            runtime_action="ALLOW",
            max_position_size=1.0,
            allowed_execution_mode="paper",
            risk_multiplier=1.0,
            cooldown_sec=0,
            stop_take_profile="default",
            reason="regime_matrix_allow",
        )

    if "REGIME_WATCH" in rec:
        return RegimeRuntimeOverride(
            runtime_action="WATCH",
            max_position_size=0.5,
            allowed_execution_mode="paper",
            risk_multiplier=0.5,
            cooldown_sec=900,
            stop_take_profile="conservative",
            reason="regime_matrix_watch",
        )

    if "CTX_BAD_REDUCE" in rec:
        return RegimeRuntimeOverride(
            runtime_action="REDUCE",
            max_position_size=0.25,
            allowed_execution_mode="paper",
            risk_multiplier=0.25,
            cooldown_sec=1800,
            stop_take_profile="defensive",
            reason="context_bad_reduce",
        )

    if "CTX_LOW_SAMPLE" in rec:
        return RegimeRuntimeOverride(
            runtime_action="WATCH",
            max_position_size=0.25,
            allowed_execution_mode="paper",
            risk_multiplier=0.25,
            cooldown_sec=1200,
            stop_take_profile="research_only",
            reason="context_low_sample",
        )

    return RegimeRuntimeOverride(
        runtime_action="NEUTRAL",
        max_position_size=1.0,
        allowed_execution_mode="paper",
        risk_multiplier=1.0,
        cooldown_sec=0,
        stop_take_profile="default",
        reason="neutral_runtime_context",
    )
