# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyRuntimeDecision:
    symbol: str
    strategy: str
    status: str
    allow_trade: bool
    watch_only: bool
    risk_multiplier: float
    reason: str


class AdaptiveStrategyController:
    """
    Русский комментарий:
    Runtime-governance для стратегий symbol+strategy.

    HEALTHY  -> торговля разрешена, risk 1.0
    WATCH    -> торговля разрешена, risk 0.5
    DEGRADED -> только наблюдение, risk 0.0
    BLOCKED  -> торговля запрещена, risk 0.0
    NO_DATA  -> только наблюдение, risk 0.0
    """

    def __init__(self, conn: Any):
        self.conn = conn

    def classify_metrics(
        self,
        *,
        trades: int,
        profit_factor: float | None,
        expectancy: float | None,
        net_pnl: float | None = None,
        min_trades: int = 20,
    ) -> tuple[str, str]:
        trades = int(trades or 0)
        pf = float(profit_factor or 0.0)
        exp = float(expectancy or 0.0)
        pnl = float(net_pnl or 0.0)

        if trades < min_trades:
            return "NO_DATA", "min_trades_not_reached"

        if pnl <= -1000 or exp <= -10:
            return "BLOCKED", "catastrophic_negative_expectancy"

        if pf >= 1.5 and exp > 0:
            return "HEALTHY", "stable_positive_expectancy"

        if pf >= 1.0 and exp > 0:
            return "WATCH", "positive_but_reduced_confidence"

        if pf < 1.0 or exp <= 0:
            return "DEGRADED", "low_pf_or_negative_expectancy"

        return "NO_DATA", "unclassified"

    def apply_recovery_hysteresis(
        self,
        *,
        symbol: str,
        strategy: str,
        candidate_status: str,
        candidate_reason: str,
    ) -> tuple[str, str]:
        """
        Русский комментарий:
        Защита от резкого восстановления:
        BLOCKED/DEGRADED не переходят сразу в HEALTHY.
        """
        try:
            current = self.get_decision(symbol, strategy)
            current_status = str(current.status or "NO_DATA").upper()
            next_status = str(candidate_status or "NO_DATA").upper()

            if current_status == "BLOCKED" and next_status in {"HEALTHY", "WATCH"}:
                cooldown_hours = float(os.getenv("BLOCKED_STRATEGY_COOLDOWN_HOURS", "6"))

                # Русский комментарий:
                # если controller работает без DB-соединения в unit-test,
                # не разрешаем мгновенный переход BLOCKED -> HEALTHY.
                if not hasattr(self, "conn") or self.conn is None:
                    return "WATCH", "recovery_step_from_blocked_no_db"

                try:
                    with self.conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT updated_at
                            FROM strategy_runtime_control
                            WHERE symbol = %s AND strategy = %s
                            """,
                            (symbol, strategy),
                        )
                        row = cur.fetchone()

                    if row and row[0] is not None:
                        with self.conn.cursor() as cur:
                            cur.execute(
                                "SELECT EXTRACT(EPOCH FROM (now() - %s)) / 3600.0",
                                (row[0],),
                            )
                            age_hours = float(cur.fetchone()[0] or 0.0)

                        if age_hours < cooldown_hours:
                            return "BLOCKED", f"blocked_cooldown_active_{round(age_hours, 2)}h_lt_{cooldown_hours}h"

                    return "WATCH", "recovery_step_from_blocked"

                except Exception:
                    return "WATCH", "recovery_step_from_blocked_db_unavailable"

            if current_status == "DEGRADED" and next_status == "HEALTHY":
                return "WATCH", "recovery_step_from_degraded"

            return next_status, candidate_reason

        except Exception:
            return str(candidate_status or "NO_DATA").upper(), candidate_reason

    def decision_from_status(
        self,
        symbol: str,
        status: str,
        strategy: str = "default",
        reason: str | None = None,
    ) -> StrategyRuntimeDecision:
        normalized = str(status or "NO_DATA").upper()
        reason = reason or ""

        if normalized == "HEALTHY":
            return StrategyRuntimeDecision(symbol, strategy, normalized, True, False, 1.0, reason or "strategy_healthy")

        if normalized == "WATCH":
            return StrategyRuntimeDecision(symbol, strategy, normalized, True, False, 0.5, reason or "strategy_watch_reduced_risk")

        if normalized == "DEGRADED":
            return StrategyRuntimeDecision(symbol, strategy, normalized, False, True, 0.0, reason or "strategy_degraded_watch_only")

        if normalized == "BLOCKED":
            return StrategyRuntimeDecision(symbol, strategy, normalized, False, True, 0.0, reason or "strategy_blocked")

        return StrategyRuntimeDecision(symbol, strategy, "NO_DATA", False, True, 0.0, reason or "strategy_no_data_watch_only")

    def upsert_decision(self, decision: StrategyRuntimeDecision, payload: dict | None = None) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategy_runtime_control (
                    symbol, strategy, status, allow_trade, watch_only,
                    risk_multiplier, reason, payload, updated_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,now())
                ON CONFLICT (symbol, strategy) DO UPDATE SET
                    status = EXCLUDED.status,
                    allow_trade = EXCLUDED.allow_trade,
                    watch_only = EXCLUDED.watch_only,
                    risk_multiplier = EXCLUDED.risk_multiplier,
                    reason = EXCLUDED.reason,
                    payload = EXCLUDED.payload,
                    updated_at = now()
                """,
                (
                    decision.symbol,
                    decision.strategy,
                    decision.status,
                    decision.allow_trade,
                    decision.watch_only,
                    decision.risk_multiplier,
                    decision.reason,
                    json.dumps(payload or {}, ensure_ascii=False, default=str),
                ),
            )
        self.conn.commit()

    def get_decision(self, symbol: str, strategy: str = "default") -> StrategyRuntimeDecision:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, strategy, status, allow_trade, watch_only, risk_multiplier, reason
                FROM strategy_runtime_control
                WHERE symbol = %s AND strategy = %s
                """,
                (symbol, strategy),
            )
            row = cur.fetchone()

        if row is None:
            return self.decision_from_status(symbol, "NO_DATA", strategy=strategy)

        return StrategyRuntimeDecision(
            symbol=str(row[0]),
            strategy=str(row[1]),
            status=str(row[2]),
            allow_trade=bool(row[3]),
            watch_only=bool(row[4]),
            risk_multiplier=float(row[5] or 0.0),
            reason=str(row[6] or ""),
        )
