# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import psycopg2
from dataclasses import dataclass
from psycopg2.extras import RealDictCursor

from finam_core.analytics.futures_pnl import FuturesPnlCalculator
from finam_core.portfolio.portfolio_equity_service import PortfolioEquityService


FUTURES_PREFIXES = ("BR", "NG", "SI", "RI", "MX")


@dataclass(frozen=True)
class PortfolioMtmSnapshot:
    base_equity: float
    live_equity: float
    unrealized_pnl: float
    used_margin: float
    free_margin: float
    margin_utilization_pct: float
    positions_count: int


class PortfolioMtmService:
    """Русский комментарий: mark-to-market портфеля по последним позициям и market_data."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam_core user=finam password=finam host=localhost",
        )
        self.futures_pnl = FuturesPnlCalculator()
        self.equity_service = PortfolioEquityService(database_url=self.database_url)

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def load_latest_positions(self) -> list[dict]:
        sql = """
        SELECT DISTINCT ON (symbol)
            symbol, qty, avg_price, ts
        FROM real_position_snapshots
        ORDER BY symbol, ts DESC
        """
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                return [dict(r) for r in cur.fetchall()]

    def load_last_price(self, symbol: str) -> float | None:
        variants = [symbol, f"{symbol}@MISX", f"{symbol}@RTSX"]

        sql = """
        SELECT close
        FROM market_data
        WHERE symbol = ANY(%s)
          AND close IS NOT NULL
        ORDER BY ts DESC
        LIMIT 1
        """

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (variants,))
                    row = cur.fetchone()
                    return float(row[0]) if row else None
        except Exception:
            return None

    def _asset_class(self, symbol: str) -> str:
        base = str(symbol or "").upper().split("@", 1)[0]
        if base.startswith(FUTURES_PREFIXES):
            return "FUTURES"
        if base.startswith(("SU", "RU")):
            return "BOND"
        return "STOCK"

    def calculate(self, *, base_equity: float) -> PortfolioMtmSnapshot:
        positions = self.load_latest_positions()
        unrealized = 0.0

        for p in positions:
            symbol = str(p.get("symbol") or "")
            qty = float(p.get("qty") or 0.0)
            avg = float(p.get("avg_price") or 0.0)

            if qty == 0 or avg <= 0:
                continue

            last = self.load_last_price(symbol)
            if last is None or last <= 0:
                continue

            asset_class = self._asset_class(symbol)

            if asset_class == "FUTURES":
                side = "BUY" if qty > 0 else "SELL"
                unrealized += self.futures_pnl.pnl(
                    symbol=symbol,
                    side=side,
                    entry=avg,
                    exit=last,
                    qty=abs(qty),
                )
            else:
                unrealized += (last - avg) * qty

        live_equity = float(base_equity) + unrealized
        eq = self.equity_service.calculate(equity=live_equity)

        return PortfolioMtmSnapshot(
            base_equity=round(float(base_equity), 2),
            live_equity=round(live_equity, 2),
            unrealized_pnl=round(unrealized, 2),
            used_margin=eq.used_margin,
            free_margin=eq.free_margin,
            margin_utilization_pct=eq.margin_utilization_pct,
            positions_count=eq.positions_count,
        )

    def save_snapshot(self, s: PortfolioMtmSnapshot) -> None:
        sql = """
        INSERT INTO portfolio_snapshots (
            ts, equity, used_margin, free_margin, margin_utilization_pct,
            raw_json
        )
        VALUES (
            now(), %s, %s, %s, %s,
            jsonb_build_object(
                'base_equity', %s,
                'live_equity', %s,
                'unrealized_pnl', %s,
                'positions_count', %s
            )
        )
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    s.live_equity,
                    s.used_margin,
                    s.free_margin,
                    s.margin_utilization_pct,
                    s.base_equity,
                    s.live_equity,
                    s.unrealized_pnl,
                    s.positions_count,
                ))
