# -*- coding: utf-8 -*-
"""
Репозиторий торговых сигналов.

Назначение:
- сохранять все торговые точки;
- хранить rejected/filled/closed lifecycle;
- не отправлять заявки;
- не зависеть от Telegram.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional


class SignalRepository:
    def __init__(self, conn: Any):
        """conn может быть соединением или фабрикой новых соединений."""
        self.conn = conn

    def _acquire_connection(self) -> tuple[Any, bool]:
        if callable(self.conn):
            return self.conn(), True
        return self.conn, False

    @staticmethod
    def _release_connection(conn: Any, managed: bool) -> None:
        if managed:
            conn.close()

    def save_signal(self, intent: dict) -> str:
        signal_id = str(intent.get("signal_id") or uuid.uuid4())

        entry_price = (
            intent.get("entry_price")
            or intent.get("price")
            or intent.get("limit_price")
        )

        stop_loss = (
            intent.get("stop_loss")
            or intent.get("stop_price")
            or intent.get("sl_price")
        )

        take_profit = (
            intent.get("take_profit")
            or intent.get("take_price")
            or intent.get("tp_price")
        )

        rr = self._calc_rr(entry_price, stop_loss, take_profit)

        conn, managed = self._acquire_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                """
                INSERT INTO signals (
                    signal_id,
                    symbol,
                    side,
                    strategy,
                    horizon,
                    timeframe,
                    regime,
                    entry_price,
                    stop_loss,
                    take_profit,
                    rr,
                    confidence,
                    status,
                    payload
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s::jsonb || CASE
                      WHEN coalesce(%s::jsonb->>'portfolio_scope','')='' THEN
                        jsonb_build_object(
                          'portfolio_scope',analytics.resolve_paper_portfolio_scope_v1(%s,'paper'),
                          'execution_type','paper')
                      ELSE '{}'::jsonb END
                )
                ON CONFLICT (signal_id) DO NOTHING
                """,
                (
                    signal_id,
                    intent.get("symbol"),
                    intent.get("side"),
                    intent.get("strategy"),
                    intent.get("horizon") or intent.get("signal_horizon") or "INTRADAY",
                    intent.get("timeframe"),
                    intent.get("regime"),
                    entry_price,
                    stop_loss,
                    take_profit,
                    rr,
                    intent.get("confidence"),
                    intent.get("status", "NEW"),
                    json.dumps(intent, ensure_ascii=False, default=str),
                    json.dumps(intent, ensure_ascii=False, default=str),
                    intent.get("symbol"),
                ),
                )
            conn.commit()
        finally:
            self._release_connection(conn, managed)
        return signal_id

    def mark_rejected(self, signal_id: str, reason: str) -> None:
        self._update_status(signal_id, "RISK_REJECTED", reason)

    def mark_accepted(self, signal_id: str) -> None:
        """Фиксирует прохождение всех admission/risk gate до исполнения."""
        self._update_status(signal_id, "RISK_ACCEPTED", None)

    def mark_filled(self, signal_id: str) -> None:
        self._update_status(signal_id, "FILLED", None)

    def link_fill(
        self,
        signal_id: str,
        fill_id: Optional[str],
        symbol: str,
        side: str,
        qty: float,
        price: float,
    ) -> None:
        conn, managed = self._acquire_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                """
                INSERT INTO signal_fills (
                    signal_id, fill_id, symbol, side, qty, price
                )
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (signal_id, fill_id, symbol, side, qty, price),
                )
            conn.commit()
        finally:
            self._release_connection(conn, managed)

    def _update_status(
        self,
        signal_id: str,
        status: str,
        rejection_reason: Optional[str],
    ) -> None:
        conn, managed = self._acquire_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                """
                UPDATE signals
                SET status = %s,
                    rejection_reason = COALESCE(%s, rejection_reason)
                WHERE signal_id = %s
                """,
                (status, rejection_reason, signal_id),
                )
            conn.commit()
        finally:
            self._release_connection(conn, managed)

    @staticmethod
    def _calc_rr(entry, stop, take) -> Optional[float]:
        if entry is None or stop is None or take is None:
            return None

        risk = abs(float(entry) - float(stop))
        reward = abs(float(take) - float(entry))

        if risk <= 0:
            return None

        return reward / risk
