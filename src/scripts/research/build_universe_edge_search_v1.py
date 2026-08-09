#!/usr/bin/env python3
"""
UNIVERSE_EDGE_SEARCH_V1

Read-only отбор инструментов для следующего edge discovery.

Не оценивает вероятность edge.
Не запускает стратегии.
Не пишет в PostgreSQL.
Не меняет runtime/execution.

Источник:
    public.market_bars
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2
import psycopg2.extras


CONFIG_PATH = Path(
    "config/research/universe_edge_search_v1.json"
)


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())



def build_calendar_freshness_map(
    conn,
    symbols,
    timeframe,
):
    """
    Calendar-aware freshness для Universe Edge Search V1.

    Не сравнивает session markets с global max(ts) 24x7 universe.

    Возвращает:
        symbol -> {
            "fresh": bool,
            "calendar_mode": str,
            "active_weekdays": tuple[int, ...],
            "missed_expected_sessions": int,
            "wall_lag_hours": float,
        }
    """
    import json
    import statistics
    from collections import defaultdict
    from datetime import timedelta
    from pathlib import Path
    from zoneinfo import ZoneInfo

    calendar_cfg_path = Path(
        "config/research/"
        "universe_trading_calendar_freshness_v1.json"
    )

    calendar_cfg = json.loads(
        calendar_cfg_path.read_text()
    )

    timezone = ZoneInfo(
        calendar_cfg["timezone"]
    )

    lookback_days = int(
        calendar_cfg["calendar_lookback_days"]
    )

    minimum_sessions = int(
        calendar_cfg[
            "minimum_sessions_per_weekday"
        ]
    )

    minimum_daily_bars = int(
        calendar_cfg[
            "minimum_daily_bars_for_active_weekday"
        ]
    )

    minimum_activity_ratio = float(
        calendar_cfg[
            "minimum_weekday_activity_ratio"
        ]
    )

    continuous_active_weekdays = int(
        calendar_cfg[
            "continuous_minimum_active_weekdays"
        ]
    )

    continuous_median_daily_bars = int(
        calendar_cfg[
            "continuous_minimum_median_daily_bars"
        ]
    )

    continuous_max_lag_hours = float(
        calendar_cfg[
            "continuous_maximum_lag_hours"
        ]
    )

    session_max_missed = int(
        calendar_cfg[
            "session_maximum_missed_sessions"
        ]
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT clock_timestamp()
            """
        )
        now_utc = cur.fetchone()[0]

        cur.execute(
            """
            SELECT symbol, ts
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
                list(symbols),
                timeframe,
                lookback_days,
            ),
        )

        rows = cur.fetchall()

    now_local = now_utc.astimezone(timezone)

    timestamps = defaultdict(list)

    for symbol, ts in rows:
        timestamps[str(symbol)].append(
            ts.astimezone(timezone)
        )

    result = {}

    for symbol in symbols:
        series = timestamps.get(symbol, [])

        if not series:
            result[symbol] = {
                "fresh": False,
                "calendar_mode": "INSUFFICIENT",
                "active_weekdays": tuple(),
                "missed_expected_sessions": 0,
                "wall_lag_hours": float("inf"),
            }
            continue

        by_date = defaultdict(list)

        for ts in series:
            by_date[ts.date()].append(ts)

        daily = []

        for trade_date, day_rows in by_date.items():
            ordered = sorted(day_rows)

            daily.append({
                "date": trade_date,
                "weekday": trade_date.weekday(),
                "bars": len(ordered),
                "first_minute":
                    ordered[0].hour * 60
                    + ordered[0].minute,
            })

        weekday_days = defaultdict(list)

        for row in daily:
            weekday_days[
                row["weekday"]
            ].append(row)

        weekday_median_bars = {}

        for weekday in range(7):
            samples = weekday_days.get(
                weekday,
                [],
            )

            if samples:
                weekday_median_bars[weekday] = (
                    statistics.median(
                        row["bars"]
                        for row in samples
                    )
                )
            else:
                weekday_median_bars[weekday] = 0.0

        maximum_weekday_bars = max(
            weekday_median_bars.values(),
            default=0.0,
        )

        active_weekdays = []

        for weekday in range(7):
            samples = weekday_days.get(
                weekday,
                [],
            )

            if len(samples) < minimum_sessions:
                continue

            median_bars = (
                weekday_median_bars[weekday]
            )

            activity_ratio = (
                median_bars
                / maximum_weekday_bars
                if maximum_weekday_bars > 0
                else 0.0
            )

            if (
                median_bars
                >= minimum_daily_bars
                and activity_ratio
                >= minimum_activity_ratio
            ):
                active_weekdays.append(
                    weekday
                )

        median_daily_bars = statistics.median(
            row["bars"]
            for row in daily
        )

        continuous = (
            len(active_weekdays)
            >= continuous_active_weekdays
            and median_daily_bars
            >= continuous_median_daily_bars
        )

        last_ts = max(series)

        wall_lag_hours = (
            now_local - last_ts
        ).total_seconds() / 3600.0

        if continuous:
            fresh = (
                wall_lag_hours
                <= continuous_max_lag_hours
            )

            result[symbol] = {
                "fresh": fresh,
                "calendar_mode":
                    "CONTINUOUS_24X7",
                "active_weekdays":
                    tuple(active_weekdays),
                "missed_expected_sessions": 0,
                "wall_lag_hours":
                    wall_lag_hours,
            }

            continue

        active_set = set(
            active_weekdays
        )

        last_date = last_ts.date()
        today = now_local.date()

        missed_sessions = 0

        current = (
            last_date
            + timedelta(days=1)
        )

        while current < today:
            if current.weekday() in active_set:
                missed_sessions += 1

            current += timedelta(days=1)

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

            current_minute = (
                now_local.hour * 60
                + now_local.minute
            )

            if (
                current_minute >= median_open
                and last_date < today
            ):
                missed_sessions += 1

        fresh = (
            missed_sessions
            <= session_max_missed
        )

        result[symbol] = {
            "fresh": fresh,
            "calendar_mode": "SESSION",
            "active_weekdays":
                tuple(active_weekdays),
            "missed_expected_sessions":
                missed_sessions,
            "wall_lag_hours":
                wall_lag_hours,
        }

    return result


def main() -> int:
    cfg = load_config()

    timeframe = cfg["timeframe"]
    minimum_bars = int(cfg["minimum_bars"])
    minimum_days = int(cfg["minimum_trading_days"])
    max_staleness = float(
        cfg["maximum_relative_staleness_hours"]
    )
    min_range_bps = float(
        cfg["minimum_median_range_bps"]
    )
    current_prefixes = tuple(
        str(x).upper()
        for x in cfg["current_branch_prefixes"]
    )
    maximum_results = int(cfg["maximum_results"])

    print("=== UNIVERSE EDGE SEARCH V1 ===")
    print("mode=research_read_only")
    print("ranking=edge_search_readiness_not_edge_probability")
    print(f"timeframe={timeframe}")
    print(f"minimum_bars={minimum_bars}")
    print(f"minimum_trading_days={minimum_days}")
    print(
        "maximum_relative_staleness_hours="
        f"{max_staleness}"
    )
    print(
        "minimum_median_range_bps="
        f"{min_range_bps}"
    )
    print(
        "current_branch_prefixes="
        + ",".join(current_prefixes)
    )
    print()

    sql = """
    WITH base AS (
        SELECT
            symbol,
            timeframe,
            ts,
            open::numeric AS open,
            high::numeric AS high,
            low::numeric AS low,
            close::numeric AS close
        FROM public.market_bars
        WHERE timeframe=%s
    ),

    global_latest AS (
        SELECT max(ts) AS max_ts
        FROM base
    ),

    per_symbol AS (
        SELECT
            symbol,
            count(*) AS bars,
            count(DISTINCT ts::date) AS trading_days,
            min(ts) AS first_ts,
            max(ts) AS last_ts,

            count(*) - count(DISTINCT ts)
                AS duplicate_rows,

            count(*) FILTER (
                WHERE open IS NULL
                   OR high IS NULL
                   OR low IS NULL
                   OR close IS NULL
                   OR high < low
                   OR high < open
                   OR high < close
                   OR low > open
                   OR low > close
                   OR close <= 0
            ) AS invalid_ohlc_rows,

            percentile_cont(0.5) WITHIN GROUP (
                ORDER BY
                    CASE
                        WHEN close > 0
                        THEN ((high-low)/close)*10000.0
                        ELSE NULL
                    END
            ) AS median_range_bps

        FROM base
        GROUP BY symbol
    ),

    enriched AS (
        SELECT
            p.*,

            extract(
                epoch FROM (g.max_ts-p.last_ts)
            ) / 3600.0 AS relative_staleness_hours

        FROM per_symbol p
        CROSS JOIN global_latest g
    )

    SELECT
        *
    FROM enriched
    ORDER BY
        relative_staleness_hours ASC,
        bars DESC,
        trading_days DESC,
        median_range_bps DESC NULLS LAST,
        symbol
    """

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )
    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(sql, (timeframe,))
            raw_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

        eligible = []
        blocked = []

        calendar_freshness = build_calendar_freshness_map(
            conn,
            [
                str(item["symbol"])
                for item in raw_rows
            ],
            timeframe,
        )

        for row in raw_rows:
            symbol = str(row["symbol"])
            symbol_upper = symbol.upper()

            reasons = []

            if int(row["bars"]) < minimum_bars:
                reasons.append("INSUFFICIENT_BARS")

            if int(row["trading_days"]) < minimum_days:
                reasons.append(
                    "INSUFFICIENT_TRADING_DAYS"
                )

            if int(row["duplicate_rows"]) > 0:
                reasons.append("DUPLICATE_TIMESTAMPS")

            if int(row["invalid_ohlc_rows"]) > 0:
                reasons.append("INVALID_OHLC")

            staleness = float(
                row["relative_staleness_hours"]
                or 0
            )

            if staleness > max_staleness:
                reasons.append("STALE_RELATIVE_TO_UNIVERSE")

            # CALENDAR_FRESHNESS_GATE_NORMALIZATION
            freshness = calendar_freshness.get(
                str(row["symbol"])
            )

            reasons = [
                reason
                for reason in reasons
                if reason != "STALE_RELATIVE_TO_UNIVERSE"
            ]

            if (
                freshness is None
                or not freshness["fresh"]
            ):
                reasons.append(
                    "STALE_RELATIVE_TO_UNIVERSE"
                )

            median_range = row["median_range_bps"]

            if (
                median_range is None
                or float(median_range) < min_range_bps
            ):
                reasons.append("LOW_BAR_RANGE")

            current_branch = any(
                symbol_upper.startswith(prefix)
                for prefix in current_prefixes
            )

            if current_branch:
                reasons.append(
                    "CURRENT_RESEARCH_BRANCH"
                )

            row["reasons"] = reasons

            if reasons:
                blocked.append(row)
            else:
                eligible.append(row)

        print("UNIVERSE_READY_ROWS")

        for rank, row in enumerate(
            eligible[:maximum_results],
            start=1,
        ):
            print(
                "UNIVERSE_READY_ROW "
                f"rank={rank} "
                f"symbol={row['symbol']} "
                f"bars={row['bars']} "
                f"trading_days={row['trading_days']} "
                f"first_ts={row['first_ts']} "
                f"last_ts={row['last_ts']} "
                "relative_staleness_hours="
                f"{float(row['relative_staleness_hours']):.2f} "
                "median_range_bps="
                f"{float(row['median_range_bps']):.4f}"
            )

        print()
        print("CURRENT_BRANCH_ROWS")

        current_rows = [
            row
            for row in blocked
            if "CURRENT_RESEARCH_BRANCH"
            in row["reasons"]
        ]

        for row in current_rows:
            print(
                "CURRENT_BRANCH_ROW "
                f"symbol={row['symbol']} "
                f"bars={row['bars']} "
                f"trading_days={row['trading_days']} "
                "reasons="
                + ",".join(row["reasons"])
            )

        print()
        print(
            "SUMMARY_ROW "
            f"universe_symbols={len(raw_rows)} "
            f"ready={len(eligible)} "
            f"blocked={len(blocked)} "
            f"current_branches={len(current_rows)}"
        )

        print("edge_probability_calculated=0")
        print("strategy_search_performed=0")
        print("freshness_model=TRADING_CALENDAR_V1")
        print("global_universe_timestamp_used_for_gate=0")
        print("calendar_activity_ratio_used=1")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("runtime_allow=0")
        print("execution_enabled=0")
        print("VERDICT=UNIVERSE_EDGE_SEARCH_V1_READY")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
