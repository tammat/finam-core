from __future__ import annotations

import argparse
from datetime import timedelta

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--trade-source", default="paper")
    args = parser.parse_args()

    timeframe = args.timeframe.upper()
    tf_minutes = timeframe_minutes(timeframe)
    calendar = MarketSessionCalendar()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_market_bar_coverage (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    closed_trade_id BIGINT NOT NULL,
                    entry_ts TIMESTAMPTZ NOT NULL,
                    exit_ts TIMESTAMPTZ NOT NULL,
                    bars_found INTEGER NOT NULL,
                    expected_bars INTEGER NOT NULL,
                    coverage_ratio NUMERIC NOT NULL,
                    replay_possible BOOLEAN NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source, closed_trade_id)
                );
            """)

            cur.execute("""
                SELECT id, entry_ts, exit_ts
                FROM closed_trade_chains_v2
                WHERE symbol=%s
                  AND trade_source=%s
                  AND UPPER(strategy)=UPPER(%s)
                  AND UPPER(timeframe)=UPPER(%s)
                ORDER BY entry_ts
            """, (args.symbol, args.trade_source, args.strategy, timeframe))

            trades = cur.fetchall()
            saved = 0

            for trade_id, entry_ts, exit_ts in trades:
                expected = max(1, int((exit_ts - entry_ts) / timedelta(minutes=tf_minutes)) + 1)

                has_open_time = calendar.has_open_time_between(
                    symbol=args.symbol,
                    start_ts=entry_ts,
                    end_ts=exit_ts,
                    step_minutes=tf_minutes,
                )

                cur.execute("""
                    SELECT count(*)
                    FROM market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND ts >= %s - (%s || ' minutes')::interval
                      AND ts <= %s + (%s || ' minutes')::interval
                """, (args.symbol, timeframe, entry_ts, tf_minutes, exit_ts, tf_minutes))

                bars_found = int(cur.fetchone()[0] or 0)
                coverage_ratio = bars_found / expected if expected else 0.0
                replay_possible = bool(has_open_time and bars_found > 0)

                if replay_possible:
                    reason = "OK"
                elif not has_open_time:
                    reason = "SESSION_CLOSED_INTERVAL"
                else:
                    reason = "NO_BARS_IN_OPEN_INTERVAL"

                cur.execute("""
                    INSERT INTO strategy_market_bar_coverage (
                        symbol, strategy, timeframe, trade_source,
                        closed_trade_id, entry_ts, exit_ts,
                        bars_found, expected_bars, coverage_ratio,
                        replay_possible, reason, created_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source, closed_trade_id)
                    DO UPDATE SET
                        bars_found=EXCLUDED.bars_found,
                        expected_bars=EXCLUDED.expected_bars,
                        coverage_ratio=EXCLUDED.coverage_ratio,
                        replay_possible=EXCLUDED.replay_possible,
                        reason=EXCLUDED.reason,
                        created_at=now()
                """, (
                    args.symbol,
                    args.strategy.upper(),
                    timeframe,
                    args.trade_source,
                    trade_id,
                    entry_ts,
                    exit_ts,
                    bars_found,
                    expected,
                    coverage_ratio,
                    replay_possible,
                    reason,
                ))

                saved += 1

        conn.commit()

    print(
        f"MARKET_BAR_COVERAGE_AUDIT_OK symbol={args.symbol} "
        f"trades={len(trades)} saved={saved}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
