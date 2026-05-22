from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeAttributionV2:
    closed_trade_id: int
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    pnl: float
    side: str
    regime: str
    heat_status: str
    risk_multiplier: float
    lifecycle_action: str
    exit_policy: str
    attribution_quality: str
    reason: str


def classify_trade_attribution_quality(
    *,
    strategy: str,
    timeframe: str,
    heat_status: str,
    lifecycle_action: str,
    exit_policy: str,
) -> tuple[str, str]:
    """
    Русский комментарий:
    Оценивает полноту атрибуции закрытой сделки.
    Это не оценка прибыльности, а качество объяснимости сделки.
    """

    missing = []

    if not strategy:
        missing.append("strategy")

    if not timeframe:
        missing.append("timeframe")

    if not heat_status or heat_status == "unknown":
        missing.append("heat_status")

    if not exit_policy:
        missing.append("exit_policy")

    if lifecycle_action in {"SYNC_LIFECYCLE_QTY", "REBUILD_LIFECYCLE_STATE"}:
        return (
            "RISK_CONTEXT_WEAK",
            f"lifecycle_state_problem:{lifecycle_action}",
        )

    if missing:
        return (
            "PARTIAL",
            "missing:" + ",".join(missing),
        )

    return (
        "FULL",
        "all_core_context_available",
    )
