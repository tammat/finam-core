# -*- coding: utf-8 -*-
"""
PositionIntentRepository.
Русский комментарий: read-only загрузка правил горизонта позиции из PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
import psycopg2


@dataclass(frozen=True)
class PositionIntentPolicy:
    symbol: str
    horizon: str
    trade_role: str
    allow_intraday_exit: bool
    allow_trailing: bool
    allow_new_buy: bool
    allow_reduce: bool
    allow_increase: bool
    enabled: bool


class PositionIntentRepository:
    def __init__(self, ttl_sec: float = 60.0) -> None:
        self.ttl_sec = float(ttl_sec)
        self._cache_ts = 0.0
        self._cache: dict[str, PositionIntentPolicy] = {}

    def _dsn(self) -> str:
        dsn = (os.getenv("DATABASE_URL") or "").strip()
        if dsn:
            return dsn

        host = os.getenv("DB_HOST", "127.0.0.1")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "finam")
        user = os.getenv("DB_USER", "finam")
        password = os.getenv("DB_PASSWORD", "")

        parts = [
            f"host={host}",
            f"port={port}",
            f"dbname={name}",
            f"user={user}",
        ]
        if password:
            parts.append(f"password={password}")
        return " ".join(parts)

    def _safe_default(self, symbol: str) -> PositionIntentPolicy:
        """Русский комментарий: неизвестную позицию не закрываем intraday-логикой."""
        return PositionIntentPolicy(
            symbol=symbol,
            horizon="swing",
            trade_role="watch_only",
            allow_intraday_exit=False,
            allow_trailing=False,
            allow_new_buy=False,
            allow_reduce=False,
            allow_increase=False,
            enabled=False,
        )

    def _refresh(self) -> None:
        now = time.time()
        if now - self._cache_ts < self.ttl_sec:
            return

        rows: dict[str, PositionIntentPolicy] = {}

        with psycopg2.connect(self._dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT symbol, horizon, trade_role, allow_intraday_exit, allow_trailing,
                           allow_new_buy, allow_reduce, allow_increase, enabled
                    FROM position_intents
                    WHERE enabled = true
                    """
                )
                for (
                    symbol,
                    horizon,
                    trade_role,
                    allow_exit,
                    allow_trailing,
                    allow_buy,
                    allow_reduce,
                    allow_increase,
                    enabled,
                ) in cur.fetchall():
                    rows[str(symbol)] = PositionIntentPolicy(
                        symbol=str(symbol),
                        horizon=str(horizon),
                        trade_role=str(trade_role),
                        allow_intraday_exit=bool(allow_exit),
                        allow_trailing=bool(allow_trailing),
                        allow_new_buy=bool(allow_buy),
                        allow_reduce=bool(allow_reduce),
                        allow_increase=bool(allow_increase),
                        enabled=bool(enabled),
                    )

        self._cache = rows
        self._cache_ts = now

    def get(self, symbol: str) -> PositionIntentPolicy:
        sym = str(symbol or "")
        try:
            self._refresh()
            return self._cache.get(sym) or self._safe_default(sym)
        except Exception:
            return self._safe_default(sym)
