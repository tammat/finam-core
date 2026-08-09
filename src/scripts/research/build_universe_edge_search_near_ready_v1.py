#!/usr/bin/env python3
"""
UNIVERSE_EDGE_SEARCH_NEAR_READY_V1

Read-only аудит инструментов, заблокированных Universe Edge Search V1.

Цель:
- не менять readiness policy;
- не вычислять вероятность edge;
- определить инструменты, наиболее близкие к RESEARCH_READY;
- показать точные blocking reasons.

PostgreSQL read-only.
Runtime/execution не изменяются.
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
    maximum_staleness = float(
        cfg["maximum_relative_staleness_hours"]
    )
    minimum_range = float(
        cfg["minimum_median_range_bps"]
    )

    current_prefixes = tuple(
        str(value).upper()
        for value in cfg["current_branch_prefixes"]
    )

    print("=== UNIVERSE EDGE SEARCH NEAR READY V1 ===")
    print("mode=research_read_only")
    print(f"timeframe={timeframe}")
    print("readiness_policy_changed=0")
    print("edge_probability_calculated=0")
    print()

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

            cur.execute(
                """
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
                latest AS (
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

                        percentile_cont(0.5)
                        WITHIN GROUP (
                            ORDER BY
                                CASE
                                    WHEN close > 0
                                    THEN (
                                        (high-low)/close
                                    ) * 10000.0
                                    ELSE NULL
                                END
                        ) AS median_range_bps

                    FROM base
                    GROUP BY symbol
                )
                SELECT
                    p.*,
                    extract(
                        epoch FROM (
                            l.max_ts-p.last_ts
                        )
                    ) / 3600.0
                        AS relative_staleness_hours
                FROM per_symbol p
                CROSS JOIN latest l
                ORDER BY symbol
                """,
                (timeframe,),
            )

            rows = [
                dict(row)
                for row in cur.fetchall()
            ]

        evaluated = []

        for row in rows:
            symbol = str(row["symbol"])
            upper = symbol.upper()

            reasons = []

            bars = int(row["bars"])
            days = int(row["trading_days"])

            staleness = float(
                row["relative_staleness_hours"]
                or 0
            )

            range_bps = (
                float(row["median_range_bps"])
                if row["median_range_bps"] is not None
                else 0.0
            )

            if bars < minimum_bars:
                reasons.append("INSUFFICIENT_BARS")

            if days < minimum_days:
                reasons.append(
                    "INSUFFICIENT_TRADING_DAYS"
                )

            if int(row["duplicate_rows"]) > 0:
                reasons.append(
                    "DUPLICATE_TIMESTAMPS"
                )

            if int(row["invalid_ohlc_rows"]) > 0:
                reasons.append("INVALID_OHLC")

            if staleness > maximum_staleness:
                reasons.append(
                    "STALE_RELATIVE_TO_UNIVERSE"
                )

            if range_bps < minimum_range:
                reasons.append("LOW_BAR_RANGE")

            if any(
                upper.startswith(prefix)
                for prefix in current_prefixes
            ):
                reasons.append(
                    "CURRENT_RESEARCH_BRANCH"
                )

            # Не weighted edge score.
            # Сортировка сначала по числу нарушенных gates,
            # затем по объективной глубине данных.
            evaluated.append({
                **row,
                "reasons": reasons,
                "failed_gates": len(reasons),
                "bars_value": bars,
                "days_value": days,
                "staleness_value": staleness,
                "range_value": range_bps,
            })

        blocked = [
            row
            for row in evaluated
            if row["reasons"]
        ]

        # Текущие BR/NG/GOLD ветки не должны занимать
        # shortlist следующего нового инструмента.
        new_asset_candidates = [
            row
            for row in blocked
            if "CURRENT_RESEARCH_BRANCH"
            not in row["reasons"]
        ]

        ranked = sorted(
            new_asset_candidates,
            key=lambda row: (
                row["failed_gates"],
                -row["days_value"],
                -row["bars_value"],
                row["staleness_value"],
                -row["range_value"],
                str(row["symbol"]),
            ),
        )

        print("NEAR_READY_ROWS")

        for rank, row in enumerate(
            ranked[:30],
            start=1,
        ):
            print(
                "NEAR_READY_ROW "
                f"rank={rank} "
                f"symbol={row['symbol']} "
                f"failed_gates={row['failed_gates']} "
                f"bars={row['bars']} "
                f"trading_days={row['trading_days']} "
                "relative_staleness_hours="
                f"{row['staleness_value']:.2f} "
                "median_range_bps="
                f"{row['range_value']:.4f} "
                "reasons="
                + ",".join(row["reasons"])
            )

        reason_counts: dict[str, int] = {}

        for row in blocked:
            for reason in row["reasons"]:
                reason_counts[reason] = (
                    reason_counts.get(reason, 0) + 1
                )

        print()
        print("BLOCK_REASON_ROWS")

        for reason, count in sorted(
            reason_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            print(
                "BLOCK_REASON_ROW "
                f"reason={reason} "
                f"symbols={count}"
            )

        one_gate = sum(
            1
            for row in new_asset_candidates
            if row["failed_gates"] == 1
        )

        two_gates = sum(
            1
            for row in new_asset_candidates
            if row["failed_gates"] == 2
        )

        print()
        print(
            "SUMMARY_ROW "
            f"universe_symbols={len(rows)} "
            f"blocked={len(blocked)} "
            f"new_asset_blocked="
            f"{len(new_asset_candidates)} "
            f"one_gate_away={one_gate} "
            f"two_gates_away={two_gates}"
        )

        print("readiness_policy_changed=0")
        print("strategy_search_performed=0")
        print("edge_probability_calculated=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(
            "VERDICT="
            "UNIVERSE_EDGE_SEARCH_NEAR_READY_V1_READY"
        )

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
