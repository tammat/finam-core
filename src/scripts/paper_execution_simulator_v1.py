from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "PAPER_EXECUTION_SIMULATOR_V1"


def d(value: Any) -> Decimal:
    return Decimal(str(value))


def pnl_for_direction(direction_code: str, entry: Decimal, exit_price: Decimal) -> Decimal:
    if direction_code == "DIRECTION_DOWN":
        return entry - exit_price
    return exit_price - entry


def simulate_one(cur, plan: dict[str, Any]) -> bool:
    symbol = plan["symbol"]
    timeframe = plan["timeframe"]
    direction = plan["direction_code"]

    entry = d(plan["entry_price"])
    stop = d(plan["invalidation_price"])
    target = d(plan["target_price"])
    risk_unit = d(plan["risk_unit"])
    horizon = int(plan["horizon_bars"])

    cur.execute(
        """
        SELECT ts, high, low, close
        FROM public.market_bars
        WHERE symbol=%s
          AND timeframe=%s
          AND ts > %s
          AND high IS NOT NULL
          AND low IS NOT NULL
          AND close IS NOT NULL
        ORDER BY ts ASC
        LIMIT %s
        """,
        (
            symbol,
            timeframe,
            plan["created_at"],
            horizon,
        ),
    )
    bars = cur.fetchall()

    if not bars:
        return False

    exit_price = d(bars[-1]["close"])
    exit_ts = bars[-1]["ts"]
    exit_reason = "TIME_EXIT"
    bars_held = len(bars)

    mae = Decimal("0")
    mfe = Decimal("0")

    for bar in bars:
        high = d(bar["high"])
        low = d(bar["low"])

        if direction == "DIRECTION_DOWN":
            adverse = high - entry
            favorable = entry - low

            if high >= stop:
                exit_price = stop
                exit_ts = bar["ts"]
                exit_reason = "STOP_HIT"
                break

            if low <= target:
                exit_price = target
                exit_ts = bar["ts"]
                exit_reason = "TARGET_HIT"
                break

        else:
            adverse = entry - low
            favorable = high - entry

            if low <= stop:
                exit_price = stop
                exit_ts = bar["ts"]
                exit_reason = "STOP_HIT"
                break

            if high >= target:
                exit_price = target
                exit_ts = bar["ts"]
                exit_reason = "TARGET_HIT"
                break

        if adverse > mae:
            mae = adverse
        if favorable > mfe:
            mfe = favorable

    pnl = pnl_for_direction(direction, entry, exit_price)
    r_multiple = pnl / risk_unit if risk_unit != 0 else Decimal("0")

    cur.execute(
        """
        INSERT INTO knowledge.paper_execution_result_v1
        (
            execution_context_id,
            recommendation_id,
            symbol,
            timeframe,
            direction_code,
            entry_price,
            exit_price,
            invalidation_price,
            target_price,
            entry_ts,
            exit_ts,
            exit_reason,
            pnl_points,
            r_multiple,
            bars_held,
            mae_points,
            mfe_points,
            evidence_json,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
        """,
        (
            plan["execution_context_id"],
            plan["recommendation_id"],
            symbol,
            timeframe,
            direction,
            entry,
            exit_price,
            stop,
            target,
            plan["created_at"],
            exit_ts,
            exit_reason,
            pnl,
            r_multiple,
            bars_held,
            mae,
            mfe,
            json.dumps(
                {
                    "mode": "paper_simulation_only",
                    "execution_allowed": 0,
                    "runtime_allowed": 0,
                    "micro_live_allowed": 0,
                    "source_execution_context_version": plan["source_version"],
                },
                ensure_ascii=False,
            ),
            SOURCE_VERSION,
        ),
    )

    return True


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    x.execution_context_id,
                    x.recommendation_id,
                    r.symbol,
                    r.timeframe,
                    x.direction_code,
                    x.entry_price,
                    x.invalidation_price,
                    x.target_price,
                    x.horizon_bars,
                    x.risk_unit,
                    x.created_at,
                    x.source_version
                FROM knowledge.recommendation_execution_context_v1 x
                JOIN knowledge.recommendation_result_v1 r
                  ON r.recommendation_id=x.recommendation_id
                WHERE x.source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
                  AND x.execution_allowed=0
                  AND x.runtime_allowed=0
                  AND x.micro_live_allowed=0
                ORDER BY x.created_at DESC
                """
            )
            plans = cur.fetchall()

            simulated = 0
            skipped = 0

            for plan in plans:
                if simulate_one(cur, dict(plan)):
                    simulated += 1
                else:
                    skipped += 1

    print("=== PAPER_EXECUTION_SIMULATOR_V1 ===")
    print(f"plans_loaded={len(plans)}")
    print(f"paper_results_created={simulated}")
    print(f"plans_skipped_no_future_bars={skipped}")
    print("mode=paper_simulation_only")
    print("paper_orders_created=0")
    print("paper_fills_created=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EXECUTION_SIMULATOR_V1_READY")


if __name__ == "__main__":
    main()
