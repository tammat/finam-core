from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeMatrixRuntimeDecision:
    score_delta: float
    confidence_delta: float
    suffix: str
    reason: str


def build_regime_matrix_runtime_decision(
    *,
    runtime_action: str,
    score_adjustment: float,
    confidence_adjustment: float,
) -> RegimeMatrixRuntimeDecision:
    """
    Русский комментарий:
    Runtime Regime Modifier v2.
    Применяет точечную поправку из strategy_regime_matrix.
    Не отправляет заявки и не включает execution напрямую.
    """
    action = runtime_action.upper()

    if action == "ALLOW":
        return RegimeMatrixRuntimeDecision(
            score_delta=max(float(score_adjustment), 0.10),
            confidence_delta=max(float(confidence_adjustment), 0.05),
            suffix="REGIME_ALLOW",
            reason="regime_matrix_allows_context",
        )

    if action == "WATCH":
        return RegimeMatrixRuntimeDecision(
            score_delta=float(score_adjustment),
            confidence_delta=float(confidence_adjustment),
            suffix="REGIME_WATCH",
            reason="regime_matrix_watch_context",
        )

    if action == "BLOCK":
        return RegimeMatrixRuntimeDecision(
            score_delta=min(float(score_adjustment), -0.30),
            confidence_delta=min(float(confidence_adjustment), -0.20),
            suffix="REGIME_BLOCK",
            reason="regime_matrix_blocks_context",
        )

    return RegimeMatrixRuntimeDecision(
        score_delta=0.0,
        confidence_delta=0.0,
        suffix="REGIME_UNKNOWN",
        reason="regime_matrix_unknown_action",
    )
