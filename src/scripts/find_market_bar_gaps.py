from __future__ import annotations

import argparse
import psycopg
from datetime import timedelta

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.session.market_session_calendar import MarketSessionCalendar


def timeframe_minutes(tf: str) -> int:
    tf = tf.upper()
    if tf == "M5":
        return 5
    if tf == "M15":
        return 15
    if tf == "H1":
        return 60
    raise ValueError(f"Unsupported timeframe: {tf}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--threshold-multiplier", type=int, default=2)
    args = parser.parse_args()

    tf_min = timeframe_minutes(args.timeframe)
    expected_delta = timedelta(minutes=tf_min)
    gap_threshold = expected_delta * args.threshold_multiplier

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_bar_gaps (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    prev_ts TIMESTAMPTZ NOT NULL,
                    next_ts TIMESTAMPTZ NOT NULL,
                    gap_minutes INTEGER NOT NULL,
                    missing_bars_estimate INTEGER NOT NULL,
                    severity TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, timeframe, prev_ts, next_ts)
                );
            """)

            cur.execute("""
                SELECT ts
                FROM market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                ORDER BY ts
            """, (args.symbol, args.timeframe))

            timestamps = [row[0] for row in cur.fetchall()]

            calendar = MarketSessionCalendar()
            gaps = 0
            session_closed = 0
            largest_gap = 0

            for prev_ts, next_ts in zip(timestamps, timestamps[1:]):
                delta = next_ts - prev_ts

                if delta <= gap_threshold:
                    continue

                # Русский комментарий: если внутри разрыва не было открытой торговой сессии,
                # не считаем такой интервал дефектом market data.
                if not calendar.has_open_time_between(
                    symbol=args.symbol,
                    start_ts=prev_ts,
                    end_ts=next_ts,
                    step_minutes=tf_min,
                ):
                    session_closed += 1
                    continue

                gap_minutes = int(delta.total_seconds() // 60)
                missing_estimate = max(0, int(gap_minutes // tf_min) - 1)

                if gap_minutes >= 60:
                    severity = "HIGH"
                elif gap_minutes >= 30:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                reason = f"gap>{args.threshold_multiplier}x_timeframe"

                cur.execute("""
                    INSERT INTO market_bar_gaps (
                        symbol, timeframe, prev_ts, next_ts,
                        gap_minutes, missing_bars_estimate,
                        severity, reason, detected_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, timeframe, prev_ts, next_ts)
                    DO UPDATE SET
                        gap_minutes=EXCLUDED.gap_minutes,
                        missing_bars_estimate=EXCLUDED.missing_bars_estimate,
                        severity=EXCLUDED.severity,
                        reason=EXCLUDED.reason,
                        detected_at=now()
                """, (
                    args.symbol,
                    args.timeframe.upper(),
                    prev_ts,
                    next_ts,
                    gap_minutes,
                    missing_estimate,
                    severity,
                    reason,
                ))

                gaps += 1
                largest_gap = max(largest_gap, gap_minutes)

            conn.commit()

    print(
        "MARKET_BAR_GAPS_OK "
        f"symbol={args.symbol} timeframe={args.timeframe.upper()} "
        f"bars={len(timestamps)} gaps={gaps} session_closed={session_closed} largest_gap_minutes={largest_gap}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
