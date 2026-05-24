from __future__ import annotations

import math

import psycopg

from finam_core.research.performance_snapshot import StrategyPerformanceSnapshot


class StrategyPerformanceRepository:
    """Русский комментарий: агрегирует статистику стратегий для Research Analytics Core."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def build_for_symbol(self, *, symbol: str, trade_source: str = "paper") -> list[StrategyPerformanceSnapshot]:
        sql = """
        SELECT
            a.strategy,
            a.symbol,
            a.timeframe,
            COALESCE(NULLIF(tcs.regime, ''), 'unknown') AS regime,
            a.trade_source,
            a.pnl::float AS pnl,
            COALESCE(NULLIF(tcs.context_quality, ''), a.attribution_quality, 'UNKNOWN') AS context_quality,
            0.0::float AS hold_sec
        FROM trade_attribution_v2 a
        LEFT JOIN trade_context_snapshots tcs
          ON tcs.closed_trade_id = a.closed_trade_id
        WHERE a.symbol = %s
          AND a.trade_source = %s
          AND COALESCE(a.strategy, '') <> ''
          AND COALESCE(a.timeframe, '') <> '';
        """

        grouped: dict[tuple[str, str, str, str, str], list[dict]] = {}

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
                    grouped.setdefault(key, []).append(
                        {
                            "pnl": float(row[5] or 0.0),
                            "context_quality": str(row[6] or "UNKNOWN"),
                            "hold_sec": float(row[7] or 0.0),
                        }
                    )

        return [self._build_snapshot(key, rows) for key, rows in grouped.items()]

    def _build_snapshot(
        self,
        key: tuple[str, str, str, str, str],
        rows: list[dict],
    ) -> StrategyPerformanceSnapshot:
        strategy, symbol, timeframe, regime, trade_source = key
        pnls = [float(x["pnl"]) for x in rows]
        trades = len(pnls)

        wins = sum(1 for x in pnls if x > 0)
        losses = sum(1 for x in pnls if x < 0)

        gross_profit = sum(x for x in pnls if x > 0)
        gross_loss_abs = abs(sum(x for x in pnls if x < 0))
        net_pnl = sum(pnls)
        gross_pnl = net_pnl

        profit_factor = gross_profit / gross_loss_abs if gross_loss_abs > 0 else (gross_profit if gross_profit > 0 else 0.0)
        winrate = wins / trades if trades else 0.0
        expectancy = net_pnl / trades if trades else 0.0

        avg_win = gross_profit / wins if wins else 0.0
        avg_loss = gross_loss_abs / losses if losses else 0.0
        avg_rr = avg_win / avg_loss if avg_loss > 0 else 0.0

        max_drawdown = self._max_drawdown(pnls)
        sharpe_like = self._sharpe_like(pnls)
        avg_hold_sec = sum(float(x["hold_sec"]) for x in rows) / trades if trades else 0.0

        full_count = sum(1 for x in rows if str(x["context_quality"]).upper() == "FULL")
        partial_count = sum(1 for x in rows if str(x["context_quality"]).upper() == "PARTIAL")
        if trades and full_count == trades:
            context_quality = "FULL"
        elif partial_count > 0 or full_count > 0:
            context_quality = "PARTIAL"
        else:
            context_quality = "UNKNOWN"

        status, reason = self._classify(trades=trades, profit_factor=profit_factor, expectancy=expectancy)

        return StrategyPerformanceSnapshot(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            trade_source=trade_source,
            trades=trades,
            wins=wins,
            losses=losses,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss_abs,
            profit_factor=profit_factor,
            winrate=winrate,
            expectancy=expectancy,
            avg_rr=avg_rr,
            max_drawdown=max_drawdown,
            sharpe_like=sharpe_like,
            avg_hold_sec=avg_hold_sec,
            context_quality=context_quality,
            status=status,
            reason=reason,
        )

    def _classify(self, *, trades: int, profit_factor: float, expectancy: float) -> tuple[str, str]:
        if trades < 30:
            return "LOW_SAMPLE", "малая_выборка"
        if profit_factor >= 1.20 and expectancy > 0:
            return "STRONG", "статистически_положительный_edge"
        if profit_factor >= 1.05 and expectancy > 0:
            return "WATCH", "умеренно_положительный_edge"
        return "WEAK", "edge_не_подтвержден"

    def _max_drawdown(self, pnls: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for pnl in pnls:
            equity += pnl
            peak = max(peak, equity)
            max_dd = min(max_dd, equity - peak)
        return abs(max_dd)

    def _sharpe_like(self, pnls: list[float]) -> float:
        if len(pnls) < 2:
            return 0.0
        mean = sum(pnls) / len(pnls)
        variance = sum((x - mean) ** 2 for x in pnls) / (len(pnls) - 1)
        std = math.sqrt(variance)
        if std <= 0:
            return 0.0
        return mean / std

    def save(self, items: list[StrategyPerformanceSnapshot]) -> int:
        sql = """
        INSERT INTO strategy_performance (
            strategy, symbol, timeframe, regime, trade_source,
            trades, wins, losses,
            gross_pnl, net_pnl, gross_profit, gross_loss,
            profit_factor, winrate, expectancy, avg_rr,
            max_drawdown, sharpe_like, avg_hold_sec,
            context_quality, status, reason
        )
        VALUES (
            %(strategy)s, %(symbol)s, %(timeframe)s, %(regime)s, %(trade_source)s,
            %(trades)s, %(wins)s, %(losses)s,
            %(gross_pnl)s, %(net_pnl)s, %(gross_profit)s, %(gross_loss)s,
            %(profit_factor)s, %(winrate)s, %(expectancy)s, %(avg_rr)s,
            %(max_drawdown)s, %(sharpe_like)s, %(avg_hold_sec)s,
            %(context_quality)s, %(status)s, %(reason)s
        )
        ON CONFLICT (strategy, symbol, timeframe, regime, trade_source)
        DO UPDATE SET
            trades = EXCLUDED.trades,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            gross_pnl = EXCLUDED.gross_pnl,
            net_pnl = EXCLUDED.net_pnl,
            gross_profit = EXCLUDED.gross_profit,
            gross_loss = EXCLUDED.gross_loss,
            profit_factor = EXCLUDED.profit_factor,
            winrate = EXCLUDED.winrate,
            expectancy = EXCLUDED.expectancy,
            avg_rr = EXCLUDED.avg_rr,
            max_drawdown = EXCLUDED.max_drawdown,
            sharpe_like = EXCLUDED.sharpe_like,
            avg_hold_sec = EXCLUDED.avg_hold_sec,
            context_quality = EXCLUDED.context_quality,
            status = EXCLUDED.status,
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
