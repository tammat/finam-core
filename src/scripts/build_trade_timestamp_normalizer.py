from __future__ import annotations

import argparse
from datetime import timedelta

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.session.market_session_calendar import MarketSessionCalendar


def session_valid(
    *,
    calendar: MarketSessionCalendar,
    symbol: str,
    entry_ts,
    exit_ts,
    step_minutes: int,
) -> bool:
    return calendar.has_open_time_between(
        symbol=symbol,
        start_ts=entry_ts,
        end_ts=exit_ts,
        step_minutes=step_minutes,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--shift-hours", type=int, default=3)
    args = parser.parse_args()

    timeframe = args.timeframe.upper()
    step_minutes = 5 if timeframe == "M5" else 15
    shift = timedelta(hours=args.shift_hours)

    calendar = MarketSessionCalendar()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trade_timestamp_normalization_audit (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    closed_trade_id BIGINT NOT NULL,

                    entry_ts_raw TIMESTAMPTZ NOT NULL,
                    exit_ts_raw TIMESTAMPTZ NOT NULL,

                    entry_ts_plus_shift TIMESTAMPTZ NOT NULL,
                    exit_ts_plus_shift TIMESTAMPTZ NOT NULL,
                    entry_ts_minus_shift TIMESTAMPTZ NOT NULL,
                    exit_ts_minus_shift TIMESTAMPTZ NOT NULL,

                    session_valid_raw BOOLEAN NOT NULL,
                    session_valid_plus_shift BOOLEAN NOT NULL,
                    session_valid_minus_shift BOOLEAN NOT NULL,

                    detected_shift_hours INTEGER NOT NULL,
                    decision TEXT NOT NULL,
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
            """, (
                args.symbol,
                args.trade_source,
                args.strategy,
                timeframe,
            ))

            rows = cur.fetchall()

            counts: dict[str, int] = {}
            saved = 0

            for closed_trade_id, entry_ts, exit_ts in rows:
                plus_entry = entry_ts + shift
                plus_exit = exit_ts + shift
                minus_entry = entry_ts - shift
                minus_exit = exit_ts - shift

                valid_raw = session_valid(
                    calendar=calendar,
                    symbol=args.symbol,
                    entry_ts=entry_ts,
                    exit_ts=exit_ts,
                    step_minutes=step_minutes,
                )
                valid_plus = session_valid(
                    calendar=calendar,
                    symbol=args.symbol,
                    entry_ts=plus_entry,
                    exit_ts=plus_exit,
                    step_minutes=step_minutes,
                )
                valid_minus = session_valid(
                    calendar=calendar,
                    symbol=args.symbol,
                    entry_ts=minus_entry,
                    exit_ts=minus_exit,
                    step_minutes=step_minutes,
                )

                detected_shift = 0
                decision = "KEEP_RAW"
                reason = "raw_session_valid"

                if valid_raw:
                    decision = "KEEP_RAW"
                    reason = "raw_session_valid"
                    detected_shift = 0
                elif valid_plus and not valid_minus:
                    decision = "SHIFT_PLUS"
                    reason = f"raw_invalid_plus_{args.shift_hours}h_valid"
                    detected_shift = args.shift_hours
                elif valid_minus and not valid_plus:
                    decision = "SHIFT_MINUS"
                    reason = f"raw_invalid_minus_{args.shift_hours}h_valid"
                    detected_shift = -args.shift_hours
                elif valid_plus and valid_minus:
                    decision = "AMBIGUOUS_SHIFT"
                    reason = "both_plus_and_minus_valid"
                    detected_shift = 0
                else:
                    decision = "INVALID_SESSION"
                    reason = "raw_and_shift_candidates_invalid"
                    detected_shift = 0

                counts[decision] = counts.get(decision, 0) + 1

                cur.execute("""
                    INSERT INTO trade_timestamp_normalization_audit (
                        symbol, strategy, timeframe, trade_source, closed_trade_id,
                        entry_ts_raw, exit_ts_raw,
                        entry_ts_plus_shift, exit_ts_plus_shift,
                        entry_ts_minus_shift, exit_ts_minus_shift,
                        session_valid_raw, session_valid_plus_shift, session_valid_minus_shift,
                        detected_shift_hours, decision, reason, created_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source, closed_trade_id)
                    DO UPDATE SET
                        entry_ts_raw=EXCLUDED.entry_ts_raw,
                        exit_ts_raw=EXCLUDED.exit_ts_raw,
                        entry_ts_plus_shift=EXCLUDED.entry_ts_plus_shift,
                        exit_ts_plus_shift=EXCLUDED.exit_ts_plus_shift,
                        entry_ts_minus_shift=EXCLUDED.entry_ts_minus_shift,
                        exit_ts_minus_shift=EXCLUDED.exit_ts_minus_shift,
                        session_valid_raw=EXCLUDED.session_valid_raw,
                        session_valid_plus_shift=EXCLUDED.session_valid_plus_shift,
                        session_valid_minus_shift=EXCLUDED.session_valid_minus_shift,
                        detected_shift_hours=EXCLUDED.detected_shift_hours,
                        decision=EXCLUDED.decision,
                        reason=EXCLUDED.reason,
                        created_at=now()
                """, (
                    args.symbol,
                    args.strategy.upper(),
                    timeframe,
                    args.trade_source,
                    closed_trade_id,
                    entry_ts,
                    exit_ts,
                    plus_entry,
                    plus_exit,
                    minus_entry,
                    minus_exit,
                    valid_raw,
                    valid_plus,
                    valid_minus,
                    detected_shift,
                    decision,
                    reason,
                ))

                saved += 1

        conn.commit()

    for decision, count in sorted(counts.items()):
        print(
            "TRADE_TIMESTAMP_NORMALIZER "
            f"symbol={args.symbol} decision={decision} count={count}",
            flush=True,
        )

    print(
        "TRADE_TIMESTAMP_NORMALIZER_SUMMARY "
        f"symbol={args.symbol} trades={len(rows)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
