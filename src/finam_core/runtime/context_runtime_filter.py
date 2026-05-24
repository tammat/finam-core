from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextRuntimeDecision:
    score_multiplier: float
    confidence_delta: float
    suffix: str
    reason: str


def build_context_runtime_decision(
    *,
    context_status: str,
    trades: int,
    profit_factor: float,
    expectancy: float,
) -> ContextRuntimeDecision:
    """Русский комментарий: мягкая корректировка runtime-score по режимной статистике."""
    status = context_status.upper()

    if trades < 10 or status == "LOW_SAMPLE":
        return ContextRuntimeDecision(
            score_multiplier=0.95,
            confidence_delta=-0.03,
            suffix="CTX_LOW_SAMPLE",
            reason="context_low_sample",
        )

    if status == "STRONG_CONTEXT":
        return ContextRuntimeDecision(
            score_multiplier=1.20,
            confidence_delta=0.10,
            suffix="CTX_STRONG_BOOST",
            reason="context_has_positive_edge",
        )

    if status == "WATCH_CONTEXT":
        return ContextRuntimeDecision(
            score_multiplier=1.08,
            confidence_delta=0.05,
            suffix="CTX_WATCH_BOOST",
            reason="context_moderately_positive",
        )

    if status == "BAD_CONTEXT" or profit_factor < 0.85 or expectancy < 0:
        return ContextRuntimeDecision(
            score_multiplier=0.55,
            confidence_delta=-0.20,
            suffix="CTX_BAD_REDUCE",
            reason="context_negative_edge",
        )

    return ContextRuntimeDecision(
        score_multiplier=1.0,
        confidence_delta=0.0,
        suffix="CTX_NEUTRAL",
        reason="context_neutral",
    )
