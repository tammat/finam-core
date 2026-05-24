from __future__ import annotations

import argparse
import os

import psycopg


def classify_matrix_action(
    *,
    context_status: str,
    trades: int,
    profit_factor: float,
    expectancy: float,
) -> tuple[str, float, float, str]:
    """Русский комментарий: переводим regime performance в runtime-action."""
    status = context_status.upper()

    if trades < 10 or status == "LOW_SAMPLE":
        return (
            "WATCH",
            -0.03,
            -0.03,
            "малая_выборка_контекста",
        )

    if status == "STRONG_CONTEXT" and profit_factor >= 1.25 and expectancy > 0:
        return (
            "ALLOW",
            0.15,
            0.10,
            "сильный_режимный_edge",
        )

    if status == "WATCH_CONTEXT" and profit_factor >= 1.05 and expectancy > 0:
        return (
            "WATCH",
            0.06,
            0.04,
            "умеренно_положительный_режимный_edge",
        )

    if status == "BAD_CONTEXT" or profit_factor < 0.85 or expectancy < 0:
        return (
            "BLOCK",
            -0.30,
            -0.20,
            "отрицательный_режимный_edge",
        )

    return (
        "WATCH",
        0.0,
        0.0,
        "нейтральный_режимный_контекст",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]

    select_sql = """
    SELECT
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime,
        trend,
        volatility,
        exit_policy,
        trades,
        net_pnl,
        profit_factor,
        expectancy,
        winrate,
        status
    FROM strategy_regime_performance
    WHERE symbol = %(symbol)s
      AND trade_source = %(trade_source)s;
    """

    insert_sql = """
    INSERT INTO strategy_regime_matrix (
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime,
        trend,
        volatility,
        exit_policy,
        trades,
        net_pnl,
        profit_factor,
        expectancy,
        winrate,
        context_status,
        runtime_action,
        score_adjustment,
        confidence_adjustment,
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
        %(net_pnl)s,
        %(profit_factor)s,
        %(expectancy)s,
        %(winrate)s,
        %(context_status)s,
        %(runtime_action)s,
        %(score_adjustment)s,
        %(confidence_adjustment)s,
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
        net_pnl = EXCLUDED.net_pnl,
        profit_factor = EXCLUDED.profit_factor,
        expectancy = EXCLUDED.expectancy,
        winrate = EXCLUDED.winrate,
        context_status = EXCLUDED.context_status,
        runtime_action = EXCLUDED.runtime_action,
        score_adjustment = EXCLUDED.score_adjustment,
        confidence_adjustment = EXCLUDED.confidence_adjustment,
        reason = EXCLUDED.reason,
        calculated_at = now();
    """

    saved = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                select_sql,
                {
                    "symbol": args.symbol,
                    "trade_source": args.trade_source,
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
                    trades,
                    net_pnl,
                    profit_factor,
                    expectancy,
                    winrate,
                    context_status,
                ) = row

                runtime_action, score_adj, confidence_adj, reason = classify_matrix_action(
                    context_status=str(context_status),
                    trades=int(trades),
                    profit_factor=float(profit_factor),
                    expectancy=float(expectancy),
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
                        "net_pnl": net_pnl,
                        "profit_factor": profit_factor,
                        "expectancy": expectancy,
                        "winrate": winrate,
                        "context_status": context_status,
                        "runtime_action": runtime_action,
                        "score_adjustment": score_adj,
                        "confidence_adjustment": confidence_adj,
                        "reason": reason,
                    },
                )
                saved += 1

        conn.commit()

    print(
        "STRATEGY_REGIME_MATRIX_V1_OK "
        f"symbol={args.symbol} saved={saved}",
        flush=True,
    )


if __name__ == "__main__":
    main()
