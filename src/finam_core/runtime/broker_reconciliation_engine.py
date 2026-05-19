from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerReconciliationIssue:
    severity: str
    category: str
    symbol: str
    reason: str


class BrokerReconciliationEngine:
    """Русский комментарий: сверяет реальные брокерские позиции с runtime execution state."""

    def classify_position(
        self,
        *,
        symbol: str,
        broker_qty: float,
        bot_executed_qty: float,
        source: str,
    ) -> BrokerReconciliationIssue | None:
        if abs(broker_qty) <= 0.0001:
            return None

        # Русский комментарий: позиции, заведённые вручную/из брокера, не считаем ошибкой execution.
        if bot_executed_qty == 0 and source != "paper_execution_bridge":
            return BrokerReconciliationIssue(
                severity="INFO",
                category="EXTERNAL_BROKER_POSITION",
                symbol=symbol,
                reason=f"external_position;broker_qty={broker_qty};source={source}",
            )

        if abs(broker_qty - bot_executed_qty) > 0.0001:
            return BrokerReconciliationIssue(
                severity="HIGH",
                category="BROKER_RUNTIME_POSITION_MISMATCH",
                symbol=symbol,
                reason=f"broker_qty={broker_qty};bot_executed_qty={bot_executed_qty};source={source}",
            )

        return None
