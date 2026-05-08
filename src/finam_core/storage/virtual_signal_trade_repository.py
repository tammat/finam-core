# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor


class VirtualSignalTradeRepository:
    """Русский комментарий: PostgreSQL-хранилище виртуальных сделок по Telegram-сигналам."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam user=finam password=finam host=localhost",
        )

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def open_trade(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        raw_json: dict | None = None,
    ) -> int:
        sql = """
        INSERT INTO virtual_signal_trades (
            symbol, side, qty, entry_price, stop_loss, take_profit, status, raw_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'OPEN', %s::jsonb)
        RETURNING id
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        str(symbol),
                        str(side).upper(),
                        float(qty),
                        float(entry_price),
                        float(stop_loss),
                        float(take_profit),
                        json.dumps(raw_json or {}, ensure_ascii=False, default=str),
                    ),
                )
                return int(cur.fetchone()[0])

    def get_latest_open_trade(self, symbol: str) -> dict | None:
        sql = """
        SELECT *
        FROM virtual_signal_trades
        WHERE symbol = %s AND status = 'OPEN'
        ORDER BY opened_at DESC, id DESC
        LIMIT 1
        """

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (str(symbol),))
                row = cur.fetchone()
                return dict(row) if row else None

    def close_trade(
        self,
        *,
        trade_id: int,
        exit_price: float,
        close_reason: str,
        pnl: float,
        r_multiple: float,
    ) -> None:
        sql = """
        UPDATE virtual_signal_trades
        SET
            status = 'CLOSED',
            closed_at = now(),
            exit_price = %s,
            close_reason = %s,
            pnl = %s,
            r_multiple = %s
        WHERE id = %s AND status = 'OPEN'
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        float(exit_price),
                        str(close_reason),
                        float(pnl),
                        float(r_multiple),
                        int(trade_id),
                    ),
                )
