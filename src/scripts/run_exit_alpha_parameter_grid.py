from __future__ import annotations

import argparse
import json
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.exit_alpha_grid import build_exit_alpha_parameter_grid_v1
from finam_core.research.exit_alpha_policy import (
    ExitAlphaPolicy,
    MarketBarForExitReplay,
    _pf,
    replay_single_trade_bar_by_bar,
)


def migrate() -> None:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_grid_results (
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
                    trades INTEGER NOT NULL,
                    evaluated_trades INTEGER NOT NULL,
                    no_bars_trades INTEGER NOT NULL,
                    old_profit_factor NUMERIC NOT NULL,
                    new_profit_factor NUMERIC NOT NULL,
                    old_expectancy NUMERIC NOT NULL,
                    new_expectancy NUMERIC NOT NULL,
                    delta_expectancy NUMERIC NOT NULL,
                    exit_reason_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source, policy_name)
                );
            """)
        conn.commit()


def load_bars(cur, symbol, timeframe, entry_ts, exit_ts):
    cur.execute("""
        SELECT ts, high, low, close
        FROM market_bars
        WHERE symbol=%s AND timeframe=%s AND ts >= %s AND ts <= %s
        ORDER BY ts
    """, (symbol, timeframe, entry_ts, exit_ts))

    return [
        MarketBarForExitReplay(ts=r[0], high=float(r[1]), low=float(r[2]), close=float(r[3]))
        for r in cur.fetchall()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--bar-timeframe", default="M5")
    args = parser.parse_args()

    migrate()
    grid = build_exit_alpha_parameter_grid_v1()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT entry_ts, exit_ts, side, entry_price, exit_price, qty, pnl
                FROM closed_trade_chains_v2
                WHERE symbol=%s
                  AND trade_source=%s
                  AND UPPER(strategy)=UPPER(%s)
                  AND UPPER(timeframe)=UPPER(%s)
                ORDER BY exit_ts
            """, (args.symbol, args.trade_source, args.strategy, args.timeframe))

            trades = cur.fetchall()

            for c in grid:
                policy = ExitAlphaPolicy(
                    strategy=args.strategy,
                    timeframe=args.timeframe,
                    stop_atr=c.stop_atr,
                    take_atr=c.take_atr,
                    trail_atr=c.trail_atr,
                    max_bars_held=c.max_bars_held,
                    policy_name=c.policy_name,
                )

                old_pnls, new_pnls, reasons = [], [], {}

                for entry_ts, exit_ts, side, entry_price, exit_price, qty, pnl in trades:
                    bars = load_bars(cur, args.symbol, args.bar_timeframe, entry_ts, exit_ts)
                    r = replay_single_trade_bar_by_bar(
                        side=side,
                        entry_price=float(entry_price),
                        original_exit_price=float(exit_price),
                        qty=float(qty),
                        policy=policy,
                        bars=bars,
                    )
                    reasons[r.exit_reason] = reasons.get(r.exit_reason, 0) + 1

                    if r.exit_reason != "NO_BARS":
                        old_pnls.append(float(pnl or r.old_pnl))
                        new_pnls.append(float(r.new_pnl))

                evaluated = len(new_pnls)
                old_exp = sum(old_pnls) / evaluated if evaluated else 0.0
                new_exp = sum(new_pnls) / evaluated if evaluated else 0.0
                old_pf = _pf(old_pnls) if evaluated else 0.0
                new_pf = _pf(new_pnls) if evaluated else 0.0

                cur.execute("""
                    INSERT INTO strategy_exit_alpha_grid_results (
                        symbol, strategy, timeframe, trade_source, policy_name,
                        stop_atr, take_atr, trail_atr, max_bars_held,
                        trades, evaluated_trades, no_bars_trades,
                        old_profit_factor, new_profit_factor,
                        old_expectancy, new_expectancy, delta_expectancy,
                        exit_reason_breakdown, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source, policy_name)
                    DO UPDATE SET
                        evaluated_trades=EXCLUDED.evaluated_trades,
                        no_bars_trades=EXCLUDED.no_bars_trades,
                        old_profit_factor=EXCLUDED.old_profit_factor,
                        new_profit_factor=EXCLUDED.new_profit_factor,
                        old_expectancy=EXCLUDED.old_expectancy,
                        new_expectancy=EXCLUDED.new_expectancy,
                        delta_expectancy=EXCLUDED.delta_expectancy,
                        exit_reason_breakdown=EXCLUDED.exit_reason_breakdown,
                        calculated_at=now()
                """, (
                    args.symbol, args.strategy.upper(), args.timeframe.upper(), args.trade_source, c.policy_name,
                    c.stop_atr, c.take_atr, c.trail_atr, c.max_bars_held,
                    len(trades), evaluated, reasons.get("NO_BARS", 0),
                    round(old_pf, 6), round(new_pf, 6),
                    round(old_exp, 6), round(new_exp, 6), round(new_exp - old_exp, 6),
                    json.dumps(reasons, ensure_ascii=False),
                ))

        conn.commit()

    print(f"EXIT_ALPHA_GRID_SUMMARY policies={len(grid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
