from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import psycopg2


@dataclass(frozen=True, slots=True)
class RegimeGuardCandidate:
    scope: str
    regime_key: str
    classification: str
    reason: str
    trades: int
    net_pnl: float
    expectancy: float
    profit_factor: Optional[float]


class RegimeGuardCandidateReader:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def load(self) -> dict[tuple[str, str], RegimeGuardCandidate]:
        sql = """
            select
                scope,
                regime_key,
                classification,
                reason,
                trades,
                net_pnl,
                expectancy,
                profit_factor
            from research_regime_guard_candidates
            where source='regime_guard_candidate_v1'
        """

        out = {}

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                for row in cur.fetchall():
                    scope, regime_key, classification, reason, trades, net_pnl, expectancy, pf = row
                    item = RegimeGuardCandidate(
                        scope=scope,
                        regime_key=regime_key,
                        classification=classification,
                        reason=reason,
                        trades=int(trades or 0),
                        net_pnl=float(net_pnl or 0),
                        expectancy=float(expectancy or 0),
                        profit_factor=None if pf is None else float(pf),
                    )
                    out[(scope, regime_key)] = item

        return out
