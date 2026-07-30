from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg

from finam_core.research.purged_split import purged_temporal_split


@dataclass(frozen=True)
class StrategyWalkForwardResult:
    strategy: str
    symbol: str
    timeframe: str
    regime: str
    trade_source: str
    train_from: datetime
    train_to: datetime
    test_from: datetime
    test_to: datetime
    train_trades: int
    test_trades: int
    train_pf: float
    test_pf: float
    train_expectancy: float
    test_expectancy: float
    train_winrate: float
    test_winrate: float
    degradation_score: float
    stability_score: float
    status: str
    reason: str


class StrategyWalkForwardRepository:
    """Русский комментарий: строит простой rolling train/test walk-forward по сделкам."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def build_for_symbol(
        self,
        *,
        symbol: str,
        trade_source: str = "paper",
        train_ratio: float = 0.7,
        min_trades: int = 30,
        embargo_minutes: int = 60,
    ) -> list[StrategyWalkForwardResult]:
        sql = """
        SELECT
            a.strategy,
            a.symbol,
            a.timeframe,
            COALESCE(NULLIF(tcs.regime, ''), 'unknown') AS regime,
            a.trade_source,
            a.pnl::float AS pnl,
            c.entry_ts,
            c.exit_ts
        FROM trade_attribution_v2 a
        JOIN closed_trade_chains_v2 c
          ON c.id = a.closed_trade_id
        LEFT JOIN trade_context_snapshots tcs
          ON tcs.closed_trade_id = a.closed_trade_id
        WHERE a.symbol = %s
          AND a.trade_source = %s
          AND COALESCE(a.strategy, '') <> ''
          AND COALESCE(a.timeframe, '') <> ''
        ORDER BY a.strategy, a.timeframe, regime, c.entry_ts, c.exit_ts;
        """

        grouped: dict[tuple[str, str, str, str, str], list[tuple[float, datetime, datetime]]] = {}

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, trade_source))
                for row in cur.fetchall():
                    key = (
                        str(row[0] or ""),
                        str(row[1] or ""),
                        str(row[2] or ""),
                        str(row[3] or "unknown"),
                        str(row[4] or trade_source),
                    )
                    grouped.setdefault(key, []).append((float(row[5] or 0.0), row[6], row[7]))

        results: list[StrategyWalkForwardResult] = []
        for key, rows in grouped.items():
            if len(rows) < max(2, min_trades):
                results.append(self._low_sample_result(key, rows))
                continue

            split = purged_temporal_split(
                rows,
                train_ratio=train_ratio,
                start=lambda row: row[1],
                end=lambda row: row[2],
                embargo=timedelta(minutes=embargo_minutes),
            )
            train = split.train
            test = split.test
            if not train or not test:
                results.append(self._low_sample_result(key, rows))
                continue
            results.append(self._build_result(key, train, test))

        return results

    def _low_sample_result(
        self,
        key: tuple[str, str, str, str, str],
        rows: list[tuple[float, datetime, datetime]],
    ) -> StrategyWalkForwardResult:
        strategy, symbol, timeframe, regime, trade_source = key
        first_ts = rows[0][1] if rows else datetime.utcnow()
        last_ts = rows[-1][2] if rows else first_ts

        return StrategyWalkForwardResult(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            trade_source=trade_source,
            train_from=first_ts,
            train_to=last_ts,
            test_from=last_ts,
            test_to=last_ts,
            train_trades=len(rows),
            test_trades=0,
            train_pf=0.0,
            test_pf=0.0,
            train_expectancy=0.0,
            test_expectancy=0.0,
            train_winrate=0.0,
            test_winrate=0.0,
            degradation_score=1.0,
            stability_score=0.0,
            status="LOW_SAMPLE",
            reason="малая_выборка_для_walkforward",
        )

    def _build_result(
        self,
        key: tuple[str, str, str, str, str],
        train: list[tuple[float, datetime, datetime]],
        test: list[tuple[float, datetime, datetime]],
    ) -> StrategyWalkForwardResult:
        strategy, symbol, timeframe, regime, trade_source = key

        train_m = self._metrics([x[0] for x in train])
        test_m = self._metrics([x[0] for x in test])

        degradation_score = max(0.0, train_m["pf"] - test_m["pf"])
        stability_score = max(0.0, min(1.0, test_m["pf"] / train_m["pf"])) if train_m["pf"] > 0 else 0.0

        status, reason = self._classify(
            train_trades=len(train),
            test_trades=len(test),
            train_pf=train_m["pf"],
            test_pf=test_m["pf"],
            test_expectancy=test_m["expectancy"],
            stability_score=stability_score,
        )

        return StrategyWalkForwardResult(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            trade_source=trade_source,
            train_from=train[0][1],
            train_to=train[-1][2],
            test_from=test[0][1],
            test_to=test[-1][2],
            train_trades=len(train),
            test_trades=len(test),
            train_pf=train_m["pf"],
            test_pf=test_m["pf"],
            train_expectancy=train_m["expectancy"],
            test_expectancy=test_m["expectancy"],
            train_winrate=train_m["winrate"],
            test_winrate=test_m["winrate"],
            degradation_score=degradation_score,
            stability_score=stability_score,
            status=status,
            reason=reason,
        )

    def _metrics(self, pnls: list[float]) -> dict[str, float]:
        trades = len(pnls)
        wins = sum(1 for x in pnls if x > 0)
        gross_profit = sum(x for x in pnls if x > 0)
        gross_loss = abs(sum(x for x in pnls if x < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        return {
            "pf": pf,
            "expectancy": sum(pnls) / trades if trades else 0.0,
            "winrate": wins / trades if trades else 0.0,
        }

    def _classify(
        self,
        *,
        train_trades: int,
        test_trades: int,
        train_pf: float,
        test_pf: float,
        test_expectancy: float,
        stability_score: float,
    ) -> tuple[str, str]:
        if train_trades < 20 or test_trades < 10:
            return "LOW_SAMPLE", "недостаточно_train_test_сделок"
        if test_pf >= 1.15 and test_expectancy > 0 and stability_score >= 0.65:
            return "OOS_CONFIRMED", "out_of_sample_edge_подтвержден"
        if test_pf >= 1.0 and test_expectancy > 0:
            return "OOS_WATCH", "out_of_sample_edge_умеренный"
        return "OOS_FAILED", "out_of_sample_edge_не_подтвержден"

    def save(self, items: list[StrategyWalkForwardResult]) -> int:
        update_sql = """
        UPDATE strategy_walkforward_results SET
            train_trades = %(train_trades)s,
            test_trades = %(test_trades)s,
            train_pf = %(train_pf)s,
            test_pf = %(test_pf)s,
            train_expectancy = %(train_expectancy)s,
            test_expectancy = %(test_expectancy)s,
            train_winrate = %(train_winrate)s,
            test_winrate = %(test_winrate)s,
            degradation_score = %(degradation_score)s,
            stability_score = %(stability_score)s,
            status = %(status)s,
            reason = %(reason)s,
            computed_at = clock_timestamp()
        WHERE id = (
            SELECT id FROM strategy_walkforward_results
            WHERE strategy = %(strategy)s AND symbol = %(symbol)s
              AND timeframe = %(timeframe)s AND regime = %(regime)s
              AND trade_source = %(trade_source)s
              AND train_from = %(train_from)s AND train_to = %(train_to)s
              AND test_from = %(test_from)s AND test_to = %(test_to)s
            ORDER BY computed_at DESC, id DESC
            LIMIT 1
        );
        """
        insert_sql = """
        INSERT INTO strategy_walkforward_results (
            strategy, symbol, timeframe, regime, trade_source,
            train_from, train_to, test_from, test_to,
            train_trades, test_trades,
            train_pf, test_pf,
            train_expectancy, test_expectancy,
            train_winrate, test_winrate,
            degradation_score, stability_score,
            status, reason
        )
        VALUES (
            %(strategy)s, %(symbol)s, %(timeframe)s, %(regime)s, %(trade_source)s,
            %(train_from)s, %(train_to)s, %(test_from)s, %(test_to)s,
            %(train_trades)s, %(test_trades)s,
            %(train_pf)s, %(test_pf)s,
            %(train_expectancy)s, %(test_expectancy)s,
            %(train_winrate)s, %(test_winrate)s,
            %(degradation_score)s, %(stability_score)s,
            %(status)s, %(reason)s
        );
        """
        saved = 0
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in items:
                    logical_key = "|".join(
                        str(value) for value in (
                            item.strategy, item.symbol, item.timeframe, item.regime,
                            item.trade_source, item.train_from, item.train_to,
                            item.test_from, item.test_to,
                        )
                    )
                    cur.execute(
                        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                        (logical_key,),
                    )
                    cur.execute(update_sql, item.__dict__)
                    if cur.rowcount == 0:
                        cur.execute(insert_sql, item.__dict__)
                    saved += 1
            conn.commit()
        return saved
