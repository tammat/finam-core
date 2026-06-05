from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import psycopg2


@dataclass(frozen=True, slots=True)
class RegimeGuardAdvisoryDecision:
    matched: bool
    scope: str
    regime_key: str
    classification: str
    reason: str
    trades: int
    expectancy: float
    profit_factor: Optional[float]
    would_block: bool
    actual_block: bool = False
    advisory_only: bool = True


class RegimeGuardAdvisoryService:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def evaluate(self) -> RegimeGuardAdvisoryDecision:
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    select distinct on (symbol)
                        symbol,
                        case
                            when expansion_flag then 'EXPANSION'
                            when compression_flag then 'COMPRESSION'
                            else 'MIXED'
                        end as regime
                    from research_feature_store
                    where timeframe='M5'
                      and symbol in ('BRN6@RTSX','NGN6@RTSX','USDRUBF@RTSX')
                    order by symbol, ts desc
                """)
                rows = dict(cur.fetchall())

                key = (
                    f"BR={rows.get('BRN6@RTSX','NA')}"
                    f"|NG={rows.get('NGN6@RTSX','NA')}"
                    f"|USD={rows.get('USDRUBF@RTSX','NA')}"
                )

                cur.execute("""
                    select classification, reason, trades, expectancy, profit_factor
                    from research_regime_guard_candidates
                    where source='regime_guard_candidate_v1'
                      and scope='ENERGY_USD'
                      and regime_key=%s
                    limit 1
                """, (key,))
                item = cur.fetchone()

        if item is None:
            return RegimeGuardAdvisoryDecision(
                matched=False,
                scope="ENERGY_USD",
                regime_key=key,
                classification="NO_MATCH",
                reason="no_candidate",
                trades=0,
                expectancy=0.0,
                profit_factor=None,
                would_block=False,
            )

        classification, reason, trades, expectancy, profit_factor = item
        return RegimeGuardAdvisoryDecision(
            matched=True,
            scope="ENERGY_USD",
            regime_key=key,
            classification=str(classification),
            reason=str(reason),
            trades=int(trades or 0),
            expectancy=float(expectancy or 0),
            profit_factor=None if profit_factor is None else float(profit_factor),
            would_block=(classification == "BLOCK_CANDIDATE"),
        )
