#!/usr/bin/env python3
"""
UNIVERSE_TRADING_CALENDAR_FRESHNESS_V1

Read-only audit календарно-корректной freshness.

Не использует global max(ts) всего universe как эталон.

Calendar contract выводится из исторических bars:
- 24x7 series -> wall-clock lag;
- session market -> active weekdays + типичное session window.

Никаких backfill/write/runtime changes.
"""

from __future__ import annotations

import json
import os
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row


CONFIG_PATH = Path(
    "config/research/"
    "universe_trading_calendar_freshness_v1.json"
)


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def minutes_of_day(ts: datetime) -> int:
    return ts.hour * 60 + ts.minute


def iter_dates(start: date, stop: date):
    current = start

    while current <= stop:
        yield current
        current += timedelta(days=1)


def main() -> int:
    cfg = load_config()

    timeframe = cfg["timeframe"]
    timezone = ZoneInfo(cfg["timezone"])
    symbols = list(cfg["audit_symbols"])

    print(
        "=== UNIVERSE TRADING CALENDAR "
        "FRESHNESS V1 ==="
    )
    print("mode=research_read_only")
    print(f"timeframe={timeframe}")
    print(f"timezone={cfg['timezone']}")
    print("global_universe_timestamp_used=0")
    print("calendar_inferred_from_history=1")
    print()

    with psycopg.connect(
        os.environ["DATABASE_URL"],
        row_factory=dict_row,
    ) as conn:
        conn.execute("SET TRANSACTION READ ONLY")

        now_utc = conn.execute(
            "SELECT clock_timestamp() AS now_utc"
        ).fetchone()["now_utc"]

        rows = conn.execute(
            """
            SELECT
                symbol,
                ts
            FROM public.market_bars
            WHERE symbol = ANY(%s)
              AND timeframe=%s
              AND ts >= (
                    clock_timestamp()
                    - (%s || ' days')::interval
              )
            ORDER BY symbol,ts
            """,
            (
                symbols,
                timeframe,
                int(cfg["calendar_lookback_days"]),
            ),
        ).fetchall()

    now_local = now_utc.astimezone(timezone)

    timestamps: dict[str, list[datetime]] = defaultdict(list)

    for row in rows:
        timestamps[str(row["symbol"])].append(
            row["ts"].astimezone(timezone)
        )

    fresh_count = 0
    stale_count = 0
    insufficient_count = 0

    print("CALENDAR_FRESHNESS_ROWS")

    for symbol in symbols:
        series = timestamps.get(symbol, [])

        if not series:
            print(
                "CALENDAR_FRESHNESS_ROW "
                f"symbol={symbol} "
                "status=INSUFFICIENT_HISTORY "
                "reason=NO_RECENT_BARS"
            )
            insufficient_count += 1
            continue

        by_date: dict[date, list[datetime]] = defaultdict(list)

        for ts in series:
            by_date[ts.date()].append(ts)

        daily = []

        for trade_date, day_rows in sorted(by_date.items()):
            ordered = sorted(day_rows)

            daily.append({
                "date": trade_date,
                "weekday": trade_date.weekday(),
                "bars": len(ordered),
                "first_minute": minutes_of_day(ordered[0]),
                "last_minute": minutes_of_day(ordered[-1]),
            })

        weekday_days: dict[int, list[dict]] = defaultdict(list)

        for row in daily:
            weekday_days[row["weekday"]].append(row)

        print(
            "WEEKDAY_PROFILE_BEGIN "
            f"symbol={symbol}"
        )

        for weekday in range(7):
            samples = weekday_days.get(weekday, [])

            if samples:
                median_weekday_bars = statistics.median(
                    row["bars"]
                    for row in samples
                )

                first_date = min(
                    row["date"]
                    for row in samples
                )
                last_date = max(
                    row["date"]
                    for row in samples
                )
            else:
                median_weekday_bars = 0
                first_date = "NONE"
                last_date = "NONE"

            print(
                "WEEKDAY_PROFILE_ROW "
                f"symbol={symbol} "
                f"weekday={weekday} "
                f"session_days={len(samples)} "
                f"median_bars={median_weekday_bars} "
                f"first_date={first_date} "
                f"last_date={last_date}"
            )


        weekday_median_bars = {}

        for weekday in range(7):
            samples = weekday_days.get(weekday, [])

            if samples:
                weekday_median_bars[weekday] = (
                    statistics.median(
                        row["bars"]
                        for row in samples
                    )
                )
            else:
                weekday_median_bars[weekday] = 0.0

        maximum_weekday_median_bars = max(
            weekday_median_bars.values(),
            default=0.0,
        )

        active_weekdays = []

        for weekday in range(7):
            samples = weekday_days.get(weekday, [])

            if len(samples) < int(
                cfg["minimum_sessions_per_weekday"]
            ):
                continue

            median_bars = weekday_median_bars[
                weekday
            ]

            activity_ratio = (
                median_bars
                / maximum_weekday_median_bars
                if maximum_weekday_median_bars > 0
                else 0.0
            )

            if (
                median_bars
                >= int(
                    cfg[
                        "minimum_daily_bars_for_active_weekday"
                    ]
                )
                and activity_ratio
                >= float(
                    cfg[
                        "minimum_weekday_activity_ratio"
                    ]
                )
            ):
                active_weekdays.append(weekday)

        median_daily_bars = statistics.median(
            row["bars"]
            for row in daily
        )

        continuous = (
            len(active_weekdays)
            >= int(
                cfg[
                    "continuous_minimum_active_weekdays"
                ]
            )
            and median_daily_bars
            >= int(
                cfg[
                    "continuous_minimum_median_daily_bars"
                ]
            )
        )

        last_ts = max(series)
        wall_lag_hours = (
            now_local - last_ts
        ).total_seconds() / 3600.0

        if continuous:
            fresh = (
                wall_lag_hours
                <= float(
                    cfg[
                        "continuous_maximum_lag_hours"
                    ]
                )
            )

            status = "FRESH" if fresh else "STALE"

            reason = (
                "CONTINUOUS_WALL_CLOCK_OK"
                if fresh
                else "CONTINUOUS_WALL_CLOCK_LAG"
            )

            missed_sessions = 0
            calendar_mode = "CONTINUOUS_24X7"

        else:
            calendar_mode = "SESSION"

            active_set = set(active_weekdays)

            last_date = last_ts.date()
            today = now_local.date()

            missed_sessions = 0

            # Полностью прошедшие календарные даты.
            for d in iter_dates(
                last_date + timedelta(days=1),
                today - timedelta(days=1),
            ):
                if d.weekday() in active_set:
                    missed_sessions += 1

            # Для текущего дня считаем сессию ожидаемой
            # только после исторически типичного открытия.
            today_samples = weekday_days.get(
                today.weekday(),
                [],
            )

            if (
                today.weekday() in active_set
                and today_samples
            ):
                median_open = int(
                    statistics.median(
                        row["first_minute"]
                        for row in today_samples
                    )
                )

                current_minute = minutes_of_day(
                    now_local
                )

                if (
                    current_minute >= median_open
                    and last_date < today
                ):
                    missed_sessions += 1

            fresh = (
                missed_sessions
                <= int(
                    cfg[
                        "session_maximum_missed_sessions"
                    ]
                )
            )

            status = "FRESH" if fresh else "STALE"

            reason = (
                "SESSION_CALENDAR_OK"
                if fresh
                else "EXPECTED_SESSION_MISSING"
            )

        if fresh:
            fresh_count += 1
        else:
            stale_count += 1

        active_weekdays_text = ",".join(
            str(value)
            for value in active_weekdays
        )

        print(
            "CALENDAR_FRESHNESS_ROW "
            f"symbol={symbol} "
            f"calendar_mode={calendar_mode} "
            f"last_ts={last_ts.isoformat()} "
            f"wall_lag_hours={wall_lag_hours:.2f} "
            f"active_weekdays="
            f"{active_weekdays_text or 'NONE'} "
            f"median_daily_bars={median_daily_bars:.1f} "
            f"missed_expected_sessions="
            f"{missed_sessions} "
            f"status={status} "
            f"reason={reason}"
        )

    print()
    print(
        "SUMMARY_ROW "
        f"symbols={len(symbols)} "
        f"fresh={fresh_count} "
        f"stale={stale_count} "
        f"insufficient={insufficient_count}"
    )

    print("global_universe_timestamp_used=0")
    print("calendar_inferred_from_history=1")
    print("readiness_policy_changed=0")
    print("backfill_executed=0")
    print("market_data_writes_performed=0")
    print("systemd_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "UNIVERSE_TRADING_CALENDAR_FRESHNESS_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
