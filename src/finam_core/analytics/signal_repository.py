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
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


def completed_bar_signal_id_v1(intent: dict) -> str | None:
    """Return one stable id per instrument/strategy/side/completed bar.

    A quote loop may evaluate the same closed M1/M5 condition many times.  The
    completed regime/event bar, rather than wall-clock evaluation time or the
    moving quote, is the causal grain of an independent signal.
    """
    features = intent.get("features") if isinstance(intent.get("features"), dict) else {}
    source = str(intent.get("source") or "")
    bar_ts = (
        intent.get("event_bar_ts")
        or intent.get("signal_bar_ts")
        or features.get("event_bar_ts")
        or features.get("signal_bar_ts")
        or features.get("regime_bar_ts")
    )
    if bar_ts is None and source == "equity_closed_bar":
        bar_ts = intent.get("ts")
    if bar_ts is None:
        return None
    if isinstance(bar_ts, datetime):
        parsed_bar_ts = bar_ts
    else:
        try:
            parsed_bar_ts = datetime.fromisoformat(str(bar_ts).replace("Z", "+00:00"))
        except ValueError:
            parsed_bar_ts = None
    if parsed_bar_ts is not None:
        if parsed_bar_ts.tzinfo is None:
            parsed_bar_ts = parsed_bar_ts.replace(tzinfo=timezone.utc)
        bar_ts = parsed_bar_ts.astimezone(timezone.utc).isoformat()
    symbol = str(intent.get("symbol") or "").upper()
    strategy = str(intent.get("strategy") or features.get("strategy") or "UNASSIGNED").upper()
    side = str(intent.get("side") or "UNKNOWN").upper()
    timeframe = str(intent.get("timeframe") or features.get("regime_timeframe") or "M5").upper()
    if timeframe in {"", "LIVE"}:
        timeframe = "M1" if symbol.startswith("NG") else "M5"
    raw = "|".join((symbol, strategy, side, timeframe, str(bar_ts)))
    return "bar-signal:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


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
        signal_id = str(completed_bar_signal_id_v1(intent) or intent.get("signal_id") or uuid.uuid4())
        intent["signal_id"] = signal_id
        symbol = str(intent.get("symbol") or "")
        raw_timeframe = str(intent.get("timeframe") or "").upper()
        normalized_timeframe = (
            ("M1" if symbol.upper().startswith("NG") else "M5")
            if raw_timeframe in {"", "LIVE"} else raw_timeframe
        )
        intent["timeframe"] = normalized_timeframe

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
                    normalized_timeframe,
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
                # Lightweight test/dummy cursors may not expose rowcount; real
                # psycopg cursors do, and report 0 for ON CONFLICT DO NOTHING.
                intent["_signal_persisted_new"] = int(getattr(cur, "rowcount", 1)) > 0
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
