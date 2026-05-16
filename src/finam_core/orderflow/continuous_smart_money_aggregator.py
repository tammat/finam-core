from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContinuousSmartMoneyResult:
    continuous_symbol: str
    source_symbols: list[str]
    smart_money_score: float
    label: str
    total_rvol: float


class ContinuousSmartMoneyAggregator:
    """Русский комментарий: агрегирует smart-money признаки нескольких фьючерсных контрактов в continuous symbol."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def aggregate_brent(self) -> ContinuousSmartMoneyResult | None:
        return self.aggregate(
            continuous_symbol="BR_CONT",
            source_symbols=["BRM6@RTSX", "BRN6@RTSX"],
        )

    def aggregate(
        self,
        continuous_symbol: str,
        source_symbols: list[str],
    ) -> ContinuousSmartMoneyResult | None:
        sql = """
        select distinct on (symbol)
            symbol,
            rvol,
            tick_velocity,
            price_velocity,
            range_pct,
            absorption_score,
            sweep_reclaim_score,
            impulse_score,
            smart_money_score,
            label,
            raw_json
        from smart_money_feature_events
        where symbol = any(%s)
        order by symbol, ts desc
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (source_symbols,))
                rows = cur.fetchall()

        if not rows:
            return None

        total_rvol = sum(float(r[1] or 0.0) for r in rows)
        if total_rvol <= 0:
            total_rvol = float(len(rows))

        def weighted(idx: int) -> float:
            return sum(float(r[idx] or 0.0) * (float(r[1] or 0.0) / total_rvol) for r in rows)

        rvol = total_rvol
        tick_velocity = weighted(2)
        price_velocity = weighted(3)
        range_pct = weighted(4)
        absorption_score = weighted(5)
        sweep_reclaim_score = weighted(6)
        impulse_score = weighted(7)
        smart_money_score = round(weighted(8), 6)

        if smart_money_score >= 0.70:
            label = "INSTITUTIONAL_GRADE"
        elif smart_money_score >= 0.45:
            label = "SMART_MONEY_CANDIDATE"
        else:
            label = "NORMAL_FLOW"

        raw = {
            "continuous_symbol": continuous_symbol,
            "source_symbols": [str(r[0]) for r in rows],
            "source": "ContinuousSmartMoneyAggregator",
        }

        insert_sql = """
        insert into smart_money_feature_events (
            symbol,
            rvol,
            tick_velocity,
            price_velocity,
            range_pct,
            absorption_score,
            sweep_reclaim_score,
            impulse_score,
            smart_money_score,
            label,
            raw_json
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    (
                        continuous_symbol,
                        round(rvol, 6),
                        round(tick_velocity, 6),
                        round(price_velocity, 6),
                        round(range_pct, 6),
                        round(absorption_score, 6),
                        round(sweep_reclaim_score, 6),
                        round(impulse_score, 6),
                        smart_money_score,
                        label,
                        json.dumps(raw, ensure_ascii=False),
                    ),
                )
            conn.commit()

        return ContinuousSmartMoneyResult(
            continuous_symbol=continuous_symbol,
            source_symbols=raw["source_symbols"],
            smart_money_score=smart_money_score,
            label=label,
            total_rvol=round(rvol, 6),
        )
