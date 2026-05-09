# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import psycopg2
from dataclasses import dataclass
from psycopg2.extras import RealDictCursor

from finam_core.risk.margin_calculator import MarginCalculator


@dataclass(frozen=True)
class PortfolioEquitySnapshot:
    equity: float
    used_margin: float
    free_margin: float
    margin_utilization_pct: float
    positions_count: int


class PortfolioEquityService:
    """Русский комментарий: считает маржинальную нагрузку по последним реальным позициям."""

    def __init__(self, database_url: str | None = None, margin_calculator: MarginCalculator | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "dbname=finam_core user=finam password=finam host=localhost",
        )
        self.margin_calculator = margin_calculator or MarginCalculator()

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

    def calculate(self, *, equity: float) -> PortfolioEquitySnapshot:
        positions = self.load_latest_positions()

        used_margin = 0.0
        for p in positions:
            symbol = str(p.get("symbol") or "")
            qty = float(p.get("qty") or 0.0)

            if qty == 0:
                continue

            m = self.margin_calculator.calculate(symbol=symbol, qty=qty)
            used_margin += m.required_initial_margin

        free_margin = float(equity) - used_margin
        utilization = (used_margin / float(equity) * 100.0) if float(equity) > 0 else 0.0

        return PortfolioEquitySnapshot(
            equity=round(float(equity), 2),
            used_margin=round(used_margin, 2),
            free_margin=round(free_margin, 2),
            margin_utilization_pct=round(utilization, 2),
            positions_count=len(positions),
        )
