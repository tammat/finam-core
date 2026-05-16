from __future__ import annotations

from typing import Any

from finam_core.data.moex_opportunity_scanner import (
    MOEXOpportunityScanner,
    OpportunityCandidate,
)


class PostgresOpportunityScanner:
    """
    Русский комментарий:
    Runtime scanner читает рассчитанные метрики из PostgreSQL
    и выбирает лучшие акции для спекулятивных intraday-стратегий.
    """

    def __init__(
        self,
        pg_logger: Any,
        scanner: MOEXOpportunityScanner | None = None,
    ) -> None:
        self.pg_logger = pg_logger
        self.scanner = scanner or MOEXOpportunityScanner()

    def top_opportunities(
        self,
        limit: int = 5,
    ) -> list[OpportunityCandidate]:
        rows = self._load_latest_metrics()

        candidates: list[OpportunityCandidate] = []

        best_by_symbol: dict[str, OpportunityCandidate] = {}

        for row in rows:
            symbol, atr_pct, rvol, turnover, spread_pct, regime = row

            candidate = self.scanner.evaluate(
                symbol=str(symbol),
                atr_pct=float(atr_pct or 0.0),
                rvol=float(rvol or 0.0),
                turnover=float(turnover or 0.0),
                spread_pct=float(spread_pct or 0.0),
                regime=str(regime or "unknown_trend_unknown_vol"),
            )

            if candidate is None:
                continue

            current = best_by_symbol.get(candidate.symbol)
            if current is None or candidate.opportunity_score > current.opportunity_score:
                best_by_symbol[candidate.symbol] = candidate

        candidates = list(best_by_symbol.values())

        return self.scanner.rank(candidates)[: int(limit)]

    def _load_latest_metrics(self) -> list[tuple]:
        sql = """
        select
            symbol,
            atr_pct,
            rvol,
            turnover,
            spread_pct,
            regime
        from market_opportunity_metrics
        where asset_class = 'EQUITY'
          and is_tradeable = true
        order by calculated_at desc
        """

        conn = getattr(self.pg_logger, "conn", None)

        if conn is None and hasattr(self.pg_logger, "_connect"):
            with self.pg_logger._connect() as runtime_conn:
                with runtime_conn.cursor() as cur:
                    cur.execute(sql)
                    return list(cur.fetchall())

        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(sql)
                return list(cur.fetchall())

        raise RuntimeError("PostgresOpportunityScanner has no connection provider")
