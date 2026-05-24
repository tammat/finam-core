from __future__ import annotations

from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class RuntimeSizingDecision:
    allowed: bool
    original_qty: float
    sized_qty: float
    risk_multiplier: float
    allocator_decision: str
    reason: str


class RuntimeExecutionSizer:
    """Русский комментарий: применяет risk_multiplier allocator к размеру paper-заявки."""

    def __init__(self, dsn: str | None = None, min_qty: float = 1.0) -> None:
        self.dsn = dsn or build_psycopg_url()
        self.min_qty = float(min_qty)

    def size(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str,
        qty: float,
    ) -> RuntimeSizingDecision:
        original_qty = float(qty)

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT risk_multiplier, allocator_decision, reason
                    FROM runtime_capital_allocator
                    WHERE symbol=%s
                      AND strategy=%s
                      AND timeframe=%s
                    LIMIT 1
                """, (symbol, strategy, timeframe))
                row = cur.fetchone()

        if not row:
            return RuntimeSizingDecision(
                allowed=False,
                original_qty=original_qty,
                sized_qty=0.0,
                risk_multiplier=0.0,
                allocator_decision="MISSING",
                reason="runtime_allocator_missing",
            )

        risk_multiplier, allocator_decision, reason = row
        risk_multiplier = float(risk_multiplier or 0.0)
        allocator_decision = str(allocator_decision or "BLOCK")

        if risk_multiplier <= 0 or allocator_decision == "BLOCK":
            return RuntimeSizingDecision(
                allowed=False,
                original_qty=original_qty,
                sized_qty=0.0,
                risk_multiplier=risk_multiplier,
                allocator_decision=allocator_decision,
                reason=f"runtime_sizing_block allocator_decision={allocator_decision} risk_multiplier={risk_multiplier} reason={reason}",
            )

        sized_qty = original_qty * risk_multiplier

        if sized_qty < self.min_qty:
            return RuntimeSizingDecision(
                allowed=False,
                original_qty=original_qty,
                sized_qty=sized_qty,
                risk_multiplier=risk_multiplier,
                allocator_decision=allocator_decision,
                reason=f"runtime_sizing_below_min_qty sized_qty={sized_qty} min_qty={self.min_qty}",
            )

        # Русский комментарий: для фьючерсов и акций пока округляем вниз до целого лота.
        sized_qty = float(int(sized_qty))

        return RuntimeSizingDecision(
            allowed=True,
            original_qty=original_qty,
            sized_qty=sized_qty,
            risk_multiplier=risk_multiplier,
            allocator_decision=allocator_decision,
            reason=f"runtime_sizing_ok original_qty={original_qty} sized_qty={sized_qty} risk_multiplier={risk_multiplier} allocator_decision={allocator_decision}",
        )
