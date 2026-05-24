from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="NGM6@RTSX")
    parser.add_argument("--strategy", default="NG_CONSERVATIVE_BREAKOUT_M1")
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runtime_rolling_strategy_stats (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trades INTEGER NOT NULL,
                    wins INTEGER NOT NULL,
                    losses INTEGER NOT NULL,
                    gross_profit NUMERIC NOT NULL,
                    gross_loss NUMERIC NOT NULL,
                    pnl NUMERIC NOT NULL,
                    profit_factor NUMERIC NOT NULL,
                    expectancy NUMERIC NOT NULL,
                    winrate NUMERIC NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe)
                );
            """)

            cur.execute("""
                SELECT pnl
                FROM trade_attribution_v2
                WHERE symbol=%s
                  AND strategy=%s
                  AND timeframe=%s
                ORDER BY created_at DESC NULLS LAST, id DESC
                LIMIT %s
            """, (args.symbol, args.strategy, args.timeframe, args.limit))

            pnls = [float(r[0] or 0.0) for r in cur.fetchall()]

            wins = [x for x in pnls if x > 0]
            losses = [x for x in pnls if x < 0]

            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))
            pnl = gross_profit - gross_loss
            trades = len(pnls)
            profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
            expectancy = pnl / trades if trades else 0.0
            winrate = len(wins) / trades if trades else 0.0

            reason = (
                f"rolling_limit={args.limit} trades={trades} "
                f"gross_profit={round(gross_profit,6)} gross_loss={round(gross_loss,6)}"
            )

            cur.execute("""
                INSERT INTO runtime_rolling_strategy_stats (
                    symbol, strategy, timeframe,
                    trades, wins, losses,
                    gross_profit, gross_loss, pnl,
                    profit_factor, expectancy, winrate,
                    reason, calculated_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                ON CONFLICT(symbol, strategy, timeframe)
                DO UPDATE SET
                    trades=EXCLUDED.trades,
                    wins=EXCLUDED.wins,
                    losses=EXCLUDED.losses,
                    gross_profit=EXCLUDED.gross_profit,
                    gross_loss=EXCLUDED.gross_loss,
                    pnl=EXCLUDED.pnl,
                    profit_factor=EXCLUDED.profit_factor,
                    expectancy=EXCLUDED.expectancy,
                    winrate=EXCLUDED.winrate,
                    reason=EXCLUDED.reason,
                    calculated_at=now()
            """, (
                args.symbol, args.strategy, args.timeframe,
                trades, len(wins), len(losses),
                gross_profit, gross_loss, pnl,
                profit_factor, expectancy, winrate,
                reason,
            ))

        conn.commit()

    print(
        "RUNTIME_ROLLING_STRATEGY_STATS "
        f"symbol={args.symbol} strategy={args.strategy} timeframe={args.timeframe} "
        f"trades={trades} pf={round(profit_factor,4)} "
        f"expectancy={round(expectancy,6)} winrate={round(winrate,4)} pnl={round(pnl,6)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
