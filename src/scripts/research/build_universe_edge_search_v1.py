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
