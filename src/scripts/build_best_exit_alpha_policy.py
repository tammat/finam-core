from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--min-evaluated", type=int, default=60)
    parser.add_argument("--min-pf", type=float, default=1.15)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_best_exit_alpha_policy (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    stop_atr NUMERIC NOT NULL,
                    take_atr NUMERIC NOT NULL,
                    trail_atr NUMERIC NOT NULL,
                    max_bars_held INTEGER NOT NULL,
                    evaluated_trades INTEGER NOT NULL,
                    no_bars_trades INTEGER NOT NULL,
                    new_profit_factor NUMERIC NOT NULL,
                    new_expectancy NUMERIC NOT NULL,
                    delta_expectancy NUMERIC NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    selected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source)
                );
            """)

            cur.execute("""
                SELECT policy_name, stop_atr, take_atr, trail_atr, max_bars_held,
                       evaluated_trades, no_bars_trades,
                       new_profit_factor, new_expectancy, delta_expectancy
                FROM strategy_exit_alpha_grid_results
                WHERE symbol=%s
                  AND UPPER(strategy)=UPPER(%s)
                  AND UPPER(timeframe)=UPPER(%s)
                  AND trade_source=%s
                  AND evaluated_trades >= %s
                  AND new_profit_factor >= %s
                  AND new_expectancy > %s
                ORDER BY new_profit_factor DESC, new_expectancy DESC, max_bars_held ASC
                LIMIT 1
            """, (
                args.symbol, args.strategy, args.timeframe, args.trade_source,
                args.min_evaluated, args.min_pf, args.min_expectancy,
            ))

            row = cur.fetchone()

            if not row:
                print(
                    "BEST_EXIT_ALPHA_POLICY_NONE "
                    f"symbol={args.symbol} strategy={args.strategy} timeframe={args.timeframe}",
                    flush=True,
                )
                conn.commit()
                return 0

            policy_name, stop_atr, take_atr, trail_atr, max_bars_held, evaluated, no_bars, pf, exp, delta = row

            status = "RADAR_EXIT_ALPHA_CANDIDATE"
            reason = (
                f"bar_replay_pf={pf} expectancy={exp} "
                f"evaluated={evaluated} no_bars={no_bars}"
            )

            cur.execute("""
                INSERT INTO strategy_best_exit_alpha_policy (
                    symbol, strategy, timeframe, trade_source,
                    policy_name, stop_atr, take_atr, trail_atr, max_bars_held,
                    evaluated_trades, no_bars_trades,
                    new_profit_factor, new_expectancy, delta_expectancy,
                    status, reason, selected_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                ON CONFLICT (symbol, strategy, timeframe, trade_source)
                DO UPDATE SET
                    policy_name=EXCLUDED.policy_name,
                    stop_atr=EXCLUDED.stop_atr,
                    take_atr=EXCLUDED.take_atr,
                    trail_atr=EXCLUDED.trail_atr,
                    max_bars_held=EXCLUDED.max_bars_held,
                    evaluated_trades=EXCLUDED.evaluated_trades,
                    no_bars_trades=EXCLUDED.no_bars_trades,
                    new_profit_factor=EXCLUDED.new_profit_factor,
                    new_expectancy=EXCLUDED.new_expectancy,
                    delta_expectancy=EXCLUDED.delta_expectancy,
                    status=EXCLUDED.status,
                    reason=EXCLUDED.reason,
                    selected_at=now()
            """, (
                args.symbol, args.strategy.upper(), args.timeframe.upper(), args.trade_source,
                policy_name, stop_atr, take_atr, trail_atr, max_bars_held,
                evaluated, no_bars, pf, exp, delta,
                status, reason,
            ))

        conn.commit()

    print(
        "BEST_EXIT_ALPHA_POLICY_SELECTED "
        f"symbol={args.symbol} strategy={args.strategy.upper()} timeframe={args.timeframe.upper()} "
        f"policy={policy_name} pf={pf} expectancy={exp} status={status}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
