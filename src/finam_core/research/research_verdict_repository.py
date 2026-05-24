from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class StrategyResearchVerdict:
    strategy: str
    symbol: str
    timeframe: str
    regime: str
    trade_source: str
    performance_status: str
    walkforward_status: str
    regime_status: str
    performance_pf: float
    walkforward_test_pf: float
    regime_pf: float
    performance_expectancy: float
    walkforward_test_expectancy: float
    regime_expectancy: float
    trades: int
    oos_trades: int
    verdict: str
    confidence: float
    reason: str


class StrategyResearchVerdictRepository:
    """Русский комментарий: согласует performance, walk-forward и regime analytics в единый research verdict."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def build_for_symbol(self, *, symbol: str, trade_source: str = "paper") -> list[StrategyResearchVerdict]:
        sql = """
        SELECT
            p.strategy,
            p.symbol,
            p.timeframe,
            p.regime,
            p.trade_source,

            COALESCE(p.status, 'UNKNOWN') AS performance_status,
            COALESCE(w.status, 'UNKNOWN') AS walkforward_status,
            COALESCE(r.status, 'UNKNOWN') AS regime_status,

            COALESCE(p.profit_factor, 0)::float AS performance_pf,
            COALESCE(w.test_pf, 0)::float AS walkforward_test_pf,
            COALESCE(r.profit_factor, 0)::float AS regime_pf,

            COALESCE(p.expectancy, 0)::float AS performance_expectancy,
            COALESCE(w.test_expectancy, 0)::float AS walkforward_test_expectancy,
            COALESCE(r.expectancy, 0)::float AS regime_expectancy,

            COALESCE(p.trades, 0)::int AS trades,
            COALESCE(w.test_trades, 0)::int AS oos_trades
        FROM strategy_performance p
        LEFT JOIN strategy_walkforward_results w
          ON w.strategy = p.strategy
         AND w.symbol = p.symbol
         AND w.timeframe = p.timeframe
         AND w.regime = p.regime
         AND w.trade_source = p.trade_source
        LEFT JOIN strategy_regime_performance r
          ON r.strategy = p.strategy
         AND r.symbol = p.symbol
         AND r.timeframe = p.timeframe
         AND r.regime = p.regime
         AND r.trade_source = p.trade_source
        WHERE p.symbol = %s
          AND p.trade_source = %s;
        """

        items: list[StrategyResearchVerdict] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, trade_source))
                for row in cur.fetchall():
                    verdict, confidence, reason = self._decide(
                        performance_status=str(row[5] or "UNKNOWN"),
                        walkforward_status=str(row[6] or "UNKNOWN"),
                        regime_status=str(row[7] or "UNKNOWN"),
                        performance_pf=float(row[8] or 0.0),
                        walkforward_test_pf=float(row[9] or 0.0),
                        regime_pf=float(row[10] or 0.0),
                        performance_expectancy=float(row[11] or 0.0),
                        walkforward_test_expectancy=float(row[12] or 0.0),
                        regime_expectancy=float(row[13] or 0.0),
                        trades=int(row[14] or 0),
                        oos_trades=int(row[15] or 0),
                    )

                    items.append(
                        StrategyResearchVerdict(
                            strategy=str(row[0] or ""),
                            symbol=str(row[1] or ""),
                            timeframe=str(row[2] or ""),
                            regime=str(row[3] or "unknown"),
                            trade_source=str(row[4] or trade_source),
                            performance_status=str(row[5] or "UNKNOWN"),
                            walkforward_status=str(row[6] or "UNKNOWN"),
                            regime_status=str(row[7] or "UNKNOWN"),
                            performance_pf=float(row[8] or 0.0),
                            walkforward_test_pf=float(row[9] or 0.0),
                            regime_pf=float(row[10] or 0.0),
                            performance_expectancy=float(row[11] or 0.0),
                            walkforward_test_expectancy=float(row[12] or 0.0),
                            regime_expectancy=float(row[13] or 0.0),
                            trades=int(row[14] or 0),
                            oos_trades=int(row[15] or 0),
                            verdict=verdict,
                            confidence=confidence,
                            reason=reason,
                        )
                    )

        return items

    def _decide(
        self,
        *,
        performance_status: str,
        walkforward_status: str,
        regime_status: str,
        performance_pf: float,
        walkforward_test_pf: float,
        regime_pf: float,
        performance_expectancy: float,
        walkforward_test_expectancy: float,
        regime_expectancy: float,
        trades: int,
        oos_trades: int,
    ) -> tuple[str, float, str]:
        # Русский комментарий: OOS сам по себе не даёт PROMOTE, если агрегатная статистика слабая.
        if trades < 30:
            return "RESEARCH_ONLY", 0.15, "малая_общая_выборка"

        if oos_trades < 10:
            return "RESEARCH_ONLY", 0.20, "малая_oos_выборка"

        aggregate_bad = performance_pf < 1.0 or performance_expectancy <= 0
        oos_good = walkforward_status == "OOS_CONFIRMED" and walkforward_test_pf >= 1.15 and walkforward_test_expectancy > 0
        regime_good = regime_pf >= 1.10 and regime_expectancy > 0
        regime_bad = regime_status == "BAD_CONTEXT" or regime_pf < 0.90

        if aggregate_bad and oos_good:
            return "WATCH_DIVERGENCE", 0.45, "oos_положительный_но_aggregate_edge_слабый"

        if aggregate_bad:
            return "BLOCK", 0.30, "aggregate_edge_не_подтвержден"

        if regime_bad:
            return "BLOCK", 0.35, "режимный_edge_отрицательный"

        if oos_good and regime_good:
            return "CANDIDATE", 0.70, "aggregate_oos_regime_edge_согласованы"

        if oos_good:
            return "WATCH", 0.55, "oos_edge_есть_но_regime_не_подтвержден"

        return "WATCH", 0.40, "edge_неполный_требуется_наблюдение"

    def save(self, items: list[StrategyResearchVerdict]) -> int:
        sql = """
        INSERT INTO strategy_research_verdicts (
            strategy, symbol, timeframe, regime, trade_source,
            performance_status, walkforward_status, regime_status,
            performance_pf, walkforward_test_pf, regime_pf,
            performance_expectancy, walkforward_test_expectancy, regime_expectancy,
            trades, oos_trades,
            verdict, confidence, reason
        )
        VALUES (
            %(strategy)s, %(symbol)s, %(timeframe)s, %(regime)s, %(trade_source)s,
            %(performance_status)s, %(walkforward_status)s, %(regime_status)s,
            %(performance_pf)s, %(walkforward_test_pf)s, %(regime_pf)s,
            %(performance_expectancy)s, %(walkforward_test_expectancy)s, %(regime_expectancy)s,
            %(trades)s, %(oos_trades)s,
            %(verdict)s, %(confidence)s, %(reason)s
        )
        ON CONFLICT (strategy, symbol, timeframe, regime, trade_source)
        DO UPDATE SET
            performance_status = EXCLUDED.performance_status,
            walkforward_status = EXCLUDED.walkforward_status,
            regime_status = EXCLUDED.regime_status,
            performance_pf = EXCLUDED.performance_pf,
            walkforward_test_pf = EXCLUDED.walkforward_test_pf,
            regime_pf = EXCLUDED.regime_pf,
            performance_expectancy = EXCLUDED.performance_expectancy,
            walkforward_test_expectancy = EXCLUDED.walkforward_test_expectancy,
            regime_expectancy = EXCLUDED.regime_expectancy,
            trades = EXCLUDED.trades,
            oos_trades = EXCLUDED.oos_trades,
            verdict = EXCLUDED.verdict,
            confidence = EXCLUDED.confidence,
            reason = EXCLUDED.reason,
            computed_at = now();
        """

        saved = 0
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in items:
                    cur.execute(sql, item.__dict__)
                    saved += 1
            conn.commit()
        return saved
