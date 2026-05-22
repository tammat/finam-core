from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.exit_alpha_policy import ExitAlphaPolicy, replay_exit_alpha_policy


def migrate() -> None:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_replay (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    trades INTEGER NOT NULL,
                    old_total_pnl NUMERIC NOT NULL,
                    new_total_pnl NUMERIC NOT NULL,
                    old_expectancy NUMERIC NOT NULL,
                    new_expectancy NUMERIC NOT NULL,
                    old_profit_factor NUMERIC NOT NULL,
                    new_profit_factor NUMERIC NOT NULL,
                    delta_expectancy NUMERIC NOT NULL,
                    delta_profit_factor NUMERIC NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source, policy_name)
                );
            """)
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    args = parser.parse_args()

    migrate()
    saved = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, strategy, timeframe, trade_source,
                       policy_name, stop_atr, take_atr, trail_atr, max_bars_held
                FROM strategy_exit_alpha_policy
                WHERE symbol=%s AND trade_source=%s
            """, (args.symbol, args.trade_source))

            for row in cur.fetchall():
                symbol, strategy, timeframe, source, policy_name, stop_atr, take_atr, trail_atr, max_bars_held = row

                cur.execute("""
                    SELECT pnl, 0 AS bars_held
                    FROM closed_trade_chains_v2
                    WHERE symbol=%s
                      AND trade_source=%s
                      AND UPPER(strategy)=UPPER(%s)
                      AND UPPER(timeframe)=UPPER(%s)
                    ORDER BY exit_ts
                """, (symbol, source, strategy, timeframe))

                trades = [(float(pnl or 0), int(bars_held or 0)) for pnl, bars_held in cur.fetchall()]

                policy = ExitAlphaPolicy(
                    strategy=strategy,
                    timeframe=timeframe,
                    stop_atr=float(stop_atr),
                    take_atr=float(take_atr),
                    trail_atr=float(trail_atr),
                    max_bars_held=int(max_bars_held),
                    policy_name=policy_name,
                )

                result = replay_exit_alpha_policy(
                    symbol=symbol,
                    strategy=strategy,
                    timeframe=timeframe,
                    trade_source=source,
                    policy=policy,
                    trades=trades,
                )

                cur.execute("""
                    INSERT INTO strategy_exit_alpha_replay (
                        symbol, strategy, timeframe, trade_source, policy_name,
                        trades, old_total_pnl, new_total_pnl,
                        old_expectancy, new_expectancy,
                        old_profit_factor, new_profit_factor,
                        delta_expectancy, delta_profit_factor,
                        calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source, policy_name)
                    DO UPDATE SET
                        trades=EXCLUDED.trades,
                        old_total_pnl=EXCLUDED.old_total_pnl,
                        new_total_pnl=EXCLUDED.new_total_pnl,
                        old_expectancy=EXCLUDED.old_expectancy,
                        new_expectancy=EXCLUDED.new_expectancy,
                        old_profit_factor=EXCLUDED.old_profit_factor,
                        new_profit_factor=EXCLUDED.new_profit_factor,
                        delta_expectancy=EXCLUDED.delta_expectancy,
                        delta_profit_factor=EXCLUDED.delta_profit_factor,
                        calculated_at=now()
                """, (
                    result.symbol, result.strategy, result.timeframe, result.trade_source,
                    result.policy_name, result.trades,
                    result.old_total_pnl, result.new_total_pnl,
                    result.old_expectancy, result.new_expectancy,
                    result.old_profit_factor, result.new_profit_factor,
                    result.delta_expectancy, result.delta_profit_factor,
                ))

                saved += 1

                print(
                    f"EXIT_ALPHA_REPLAY symbol={result.symbol} strategy={result.strategy} "
                    f"timeframe={result.timeframe} trades={result.trades} "
                    f"old_pf={result.old_profit_factor} new_pf={result.new_profit_factor} "
                    f"old_exp={result.old_expectancy} new_exp={result.new_expectancy}",
                    flush=True,
                )

        conn.commit()

    print(f"EXIT_ALPHA_REPLAY_SUMMARY symbol={args.symbol} saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
