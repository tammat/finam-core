from __future__ import annotations

import argparse
import json

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.exit_alpha_policy import (
    ExitAlphaPolicy,
    MarketBarForExitReplay,
    _pf,
    replay_single_trade_bar_by_bar,
)
from finam_core.session.market_session_calendar import MarketSessionCalendar


def timeframe_minutes(timeframe: str) -> int:
    tf = str(timeframe or "").upper()
    if tf == "M5":
        return 5
    if tf == "M15":
        return 15
    if tf == "H1":
        return 60
    return 5


def migrate() -> None:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_bar_replay (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    trades INTEGER NOT NULL,
                    evaluated_trades INTEGER NOT NULL DEFAULT 0,
                    no_bars_trades INTEGER NOT NULL DEFAULT 0,
                    session_closed_trades INTEGER NOT NULL DEFAULT 0,
                    old_profit_factor NUMERIC NOT NULL,
                    new_profit_factor NUMERIC NOT NULL,
                    old_expectancy NUMERIC NOT NULL,
                    new_expectancy NUMERIC NOT NULL,
                    delta_expectancy NUMERIC NOT NULL,
                    exit_reason_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source, policy_name)
                );

                ALTER TABLE strategy_exit_alpha_bar_replay
                ADD COLUMN IF NOT EXISTS session_closed_trades INTEGER NOT NULL DEFAULT 0;
            """)
        conn.commit()


def load_bars(cur, *, symbol: str, timeframe: str, entry_ts, exit_ts, tf_minutes: int) -> list[MarketBarForExitReplay]:
    cur.execute("""
        SELECT ts, high, low, close
        FROM market_bars
        WHERE symbol=%s
          AND timeframe=%s
          AND ts >= %s - (%s || ' minutes')::interval
          AND ts <= %s + (%s || ' minutes')::interval
        ORDER BY ts
    """, (symbol, timeframe, entry_ts, tf_minutes, exit_ts, tf_minutes))

    return [
        MarketBarForExitReplay(
            ts=row[0],
            high=float(row[1]),
            low=float(row[2]),
            close=float(row[3]),
        )
        for row in cur.fetchall()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--bar-timeframe", default="M5")
    args = parser.parse_args()

    bar_tf = args.bar_timeframe.upper()
    tf_minutes = timeframe_minutes(bar_tf)
    calendar = MarketSessionCalendar()

    migrate()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, strategy, timeframe, trade_source,
                       policy_name, stop_atr, take_atr, trail_atr, max_bars_held
                FROM strategy_exit_alpha_policy
                WHERE symbol=%s
                  AND trade_source=%s
                ORDER BY strategy, timeframe
            """, (args.symbol, args.trade_source))

            policies = cur.fetchall()

            for row in policies:
                symbol, strategy, timeframe, source, policy_name, stop_atr, take_atr, trail_atr, max_bars_held = row

                policy = ExitAlphaPolicy(
                    strategy=strategy,
                    timeframe=timeframe,
                    stop_atr=float(stop_atr),
                    take_atr=float(take_atr),
                    trail_atr=float(trail_atr),
                    max_bars_held=int(max_bars_held),
                    policy_name=policy_name,
                )

                cur.execute("""
                    SELECT entry_ts, exit_ts, side, entry_price, exit_price, qty, pnl
                    FROM closed_trade_chains_v2
                    WHERE symbol=%s
                      AND trade_source=%s
                      AND UPPER(strategy)=UPPER(%s)
                      AND UPPER(timeframe)=UPPER(%s)
                    ORDER BY exit_ts
                """, (symbol, source, strategy, timeframe))

                trades = cur.fetchall()

                old_pnls: list[float] = []
                new_pnls: list[float] = []
                reasons: dict[str, int] = {}

                for entry_ts, exit_ts, side, entry_price, exit_price, qty, pnl in trades:
                    has_open_time = calendar.has_open_time_between(
                        symbol=symbol,
                        start_ts=entry_ts,
                        end_ts=exit_ts,
                        step_minutes=tf_minutes,
                    )

                    if not has_open_time:
                        reasons["SESSION_CLOSED_INTERVAL"] = reasons.get("SESSION_CLOSED_INTERVAL", 0) + 1
                        continue

                    bars = load_bars(
                        cur,
                        symbol=symbol,
                        timeframe=bar_tf,
                        entry_ts=entry_ts,
                        exit_ts=exit_ts,
                        tf_minutes=tf_minutes,
                    )

                    result = replay_single_trade_bar_by_bar(
                        side=side,
                        entry_price=float(entry_price),
                        original_exit_price=float(exit_price),
                        qty=float(qty),
                        policy=policy,
                        bars=bars,
                    )

                    reasons[result.exit_reason] = reasons.get(result.exit_reason, 0) + 1

                    if result.exit_reason != "NO_BARS":
                        old_pnls.append(float(pnl or result.old_pnl))
                        new_pnls.append(float(result.new_pnl))

                evaluated = len(new_pnls)
                no_bars = reasons.get("NO_BARS", 0)
                session_closed = reasons.get("SESSION_CLOSED_INTERVAL", 0)

                old_exp = sum(old_pnls) / evaluated if evaluated else 0.0
                new_exp = sum(new_pnls) / evaluated if evaluated else 0.0
                old_pf = _pf(old_pnls) if evaluated else 0.0
                new_pf = _pf(new_pnls) if evaluated else 0.0

                cur.execute("""
                    INSERT INTO strategy_exit_alpha_bar_replay (
                        symbol, strategy, timeframe, trade_source, policy_name,
                        trades, evaluated_trades, no_bars_trades, session_closed_trades,
                        old_profit_factor, new_profit_factor,
                        old_expectancy, new_expectancy, delta_expectancy,
                        exit_reason_breakdown, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source, policy_name)
                    DO UPDATE SET
                        trades=EXCLUDED.trades,
                        evaluated_trades=EXCLUDED.evaluated_trades,
                        no_bars_trades=EXCLUDED.no_bars_trades,
                        session_closed_trades=EXCLUDED.session_closed_trades,
                        old_profit_factor=EXCLUDED.old_profit_factor,
                        new_profit_factor=EXCLUDED.new_profit_factor,
                        old_expectancy=EXCLUDED.old_expectancy,
                        new_expectancy=EXCLUDED.new_expectancy,
                        delta_expectancy=EXCLUDED.delta_expectancy,
                        exit_reason_breakdown=EXCLUDED.exit_reason_breakdown,
                        calculated_at=now()
                """, (
                    symbol,
                    strategy,
                    timeframe,
                    source,
                    policy_name,
                    len(trades),
                    evaluated,
                    no_bars,
                    session_closed,
                    round(old_pf, 6),
                    round(new_pf, 6),
                    round(old_exp, 6),
                    round(new_exp, 6),
                    round(new_exp - old_exp, 6),
                    json.dumps(reasons, ensure_ascii=False),
                ))

                print(
                    "EXIT_ALPHA_BAR_REPLAY "
                    f"symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"bar_tf={bar_tf} trades={len(trades)} evaluated={evaluated} "
                    f"no_bars={no_bars} session_closed={session_closed} "
                    f"old_pf={round(old_pf, 6)} new_pf={round(new_pf, 6)} "
                    f"old_exp={round(old_exp, 6)} new_exp={round(new_exp, 6)} "
                    f"reasons={reasons}",
                    flush=True,
                )

        conn.commit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
