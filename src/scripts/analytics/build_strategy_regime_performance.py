from __future__ import annotations

import argparse
import os

import psycopg


def classify_status(*, trades: int, profit_factor: float, expectancy: float, winrate: float) -> tuple[str, str]:
    """Русский комментарий: v1-оценка устойчивости стратегии в конкретном рыночном контексте."""
    if trades < 10:
        return "LOW_SAMPLE", "малая_выборка"

    if profit_factor >= 1.25 and expectancy > 0 and winrate >= 0.45:
        return "STRONG_CONTEXT", "контекст_дает_положительный_edge"

    if profit_factor >= 1.05 and expectancy > 0:
        return "WATCH_CONTEXT", "контекст_умеренно_положительный"

    if profit_factor < 0.85 or expectancy < 0:
        return "BAD_CONTEXT", "контекст_ухудшает_результат"

    return "NEUTRAL_CONTEXT", "контекст_нейтральный"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--min-context-quality", default="FULL")
    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH base AS (
        SELECT
            tcs.symbol,
            tcs.strategy,
            tcs.timeframe,
            tcs.trade_source,
            tcs.regime,
            tcs.trend,
            tcs.volatility,
            tcs.exit_policy,
            tcs.context_quality,
            ta.pnl::float AS net_pnl
        FROM trade_context_snapshots tcs
        JOIN trade_attribution_v2 ta
          ON ta.closed_trade_id = tcs.closed_trade_id
        WHERE tcs.symbol = %(symbol)s
          AND tcs.trade_source = %(trade_source)s
          AND tcs.context_quality = %(context_quality)s
          AND tcs.regime <> 'unknown'
          AND tcs.trend <> 'unknown'
          AND tcs.volatility <> 'unknown'
          AND COALESCE(tcs.exit_policy, '') <> ''
    )
    SELECT
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime,
        trend,
        volatility,
        exit_policy,
        context_quality,
        COUNT(*)::int AS trades,
        COUNT(*) FILTER (WHERE net_pnl > 0)::int AS wins,
        COUNT(*) FILTER (WHERE net_pnl < 0)::int AS losses,
        COALESCE(SUM(net_pnl), 0)::float AS net_pnl,
        COALESCE(AVG(net_pnl), 0)::float AS avg_pnl,
        COALESCE(AVG(net_pnl) FILTER (WHERE net_pnl > 0), 0)::float AS avg_win,
        COALESCE(AVG(net_pnl) FILTER (WHERE net_pnl < 0), 0)::float AS avg_loss,
        COALESCE(SUM(net_pnl) FILTER (WHERE net_pnl > 0), 0)::float AS gross_profit,
        ABS(COALESCE(SUM(net_pnl) FILTER (WHERE net_pnl < 0), 0))::float AS gross_loss
    FROM base
    GROUP BY
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime,
        trend,
        volatility,
        exit_policy,
        context_quality;
    """

    insert_sql = """
    INSERT INTO strategy_regime_performance (
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime,
        trend,
        volatility,
        exit_policy,
        trades,
        wins,
        losses,
        winrate,
        net_pnl,
        avg_pnl,
        avg_win,
        avg_loss,
        profit_factor,
        expectancy,
        context_quality,
        status,
        reason
    )
    VALUES (
        %(symbol)s,
        %(strategy)s,
        %(timeframe)s,
        %(trade_source)s,
        %(regime)s,
        %(trend)s,
        %(volatility)s,
        %(exit_policy)s,
        %(trades)s,
        %(wins)s,
        %(losses)s,
        %(winrate)s,
        %(net_pnl)s,
        %(avg_pnl)s,
        %(avg_win)s,
        %(avg_loss)s,
        %(profit_factor)s,
        %(expectancy)s,
        %(context_quality)s,
        %(status)s,
        %(reason)s
    )
    ON CONFLICT (
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime,
        trend,
        volatility,
        exit_policy
    )
    DO UPDATE SET
        trades = EXCLUDED.trades,
        wins = EXCLUDED.wins,
        losses = EXCLUDED.losses,
        winrate = EXCLUDED.winrate,
        net_pnl = EXCLUDED.net_pnl,
        avg_pnl = EXCLUDED.avg_pnl,
        avg_win = EXCLUDED.avg_win,
        avg_loss = EXCLUDED.avg_loss,
        profit_factor = EXCLUDED.profit_factor,
        expectancy = EXCLUDED.expectancy,
        context_quality = EXCLUDED.context_quality,
        status = EXCLUDED.status,
        reason = EXCLUDED.reason,
        calculated_at = now();
    """

    saved = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "symbol": args.symbol,
                    "trade_source": args.trade_source,
                    "context_quality": args.min_context_quality,
                },
            )
            rows = cur.fetchall()

            for row in rows:
                (
                    symbol,
                    strategy,
                    timeframe,
                    trade_source,
                    regime,
                    trend,
                    volatility,
                    exit_policy,
                    context_quality,
                    trades,
                    wins,
                    losses,
                    net_pnl,
                    avg_pnl,
                    avg_win,
                    avg_loss,
                    gross_profit,
                    gross_loss,
                ) = row

                winrate = float(wins) / float(trades) if trades else 0.0
                profit_factor = float(gross_profit) / float(gross_loss) if gross_loss else 0.0
                expectancy = float(avg_pnl)

                status, reason = classify_status(
                    trades=int(trades),
                    profit_factor=profit_factor,
                    expectancy=expectancy,
                    winrate=winrate,
                )

                cur.execute(
                    insert_sql,
                    {
                        "symbol": symbol,
                        "strategy": strategy,
                        "timeframe": timeframe,
                        "trade_source": trade_source,
                        "regime": regime,
                        "trend": trend,
                        "volatility": volatility,
                        "exit_policy": exit_policy,
                        "trades": int(trades),
                        "wins": int(wins),
                        "losses": int(losses),
                        "winrate": winrate,
                        "net_pnl": net_pnl,
                        "avg_pnl": avg_pnl,
                        "avg_win": avg_win,
                        "avg_loss": avg_loss,
                        "profit_factor": profit_factor,
                        "expectancy": expectancy,
                        "context_quality": context_quality,
                        "status": status,
                        "reason": reason,
                    },
                )
                saved += 1

        conn.commit()

    print(
        "STRATEGY_REGIME_PERFORMANCE_V1_OK "
        f"symbol={args.symbol} saved={saved}",
        flush=True,
    )


if __name__ == "__main__":
    main()
