# -*- coding: utf-8 -*-

from __future__ import annotations

import json
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
    Управляет runtime-режимом стратегии по результатам performance monitor.

    HEALTHY  -> торговля разрешена, риск 1.0
    WATCH    -> торговля разрешена, риск 0.5
    DEGRADED -> только наблюдение, риск 0.0
    NO_DATA  -> только наблюдение, риск 0.0
    """

    def __init__(self, conn: Any):
        self.conn = conn

    def decision_from_status(self, symbol: str, status: str, strategy: str = "default") -> StrategyRuntimeDecision:
        normalized = str(status or "NO_DATA").upper()

        if normalized == "HEALTHY":
            return StrategyRuntimeDecision(
                symbol=symbol,
                strategy=strategy,
                status=normalized,
                allow_trade=True,
                watch_only=False,
                risk_multiplier=1.0,
                reason="strategy_healthy",
            )

        if normalized == "WATCH":
            return StrategyRuntimeDecision(
                symbol=symbol,
                strategy=strategy,
                status=normalized,
                allow_trade=True,
                watch_only=False,
                risk_multiplier=0.5,
                reason="strategy_watch_reduced_risk",
            )

        if normalized == "DEGRADED":
            return StrategyRuntimeDecision(
                symbol=symbol,
                strategy=strategy,
                status=normalized,
                allow_trade=False,
                watch_only=True,
                risk_multiplier=0.0,
                reason="strategy_degraded_watch_only",
            )

        return StrategyRuntimeDecision(
            symbol=symbol,
            strategy=strategy,
            status="NO_DATA",
            allow_trade=False,
            watch_only=True,
            risk_multiplier=0.0,
            reason="strategy_no_data_watch_only",
        )

    def upsert_decision(self, decision: StrategyRuntimeDecision, payload: dict | None = None) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategy_runtime_control (
                    symbol,
                    strategy,
                    status,
                    allow_trade,
                    watch_only,
                    risk_multiplier,
                    reason,
                    payload,
                    updated_at
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
