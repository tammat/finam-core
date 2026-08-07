#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


TARGET_BATCH = "PG_EDGE_FAMILY_EXPANSION_V1_20260806_073217"
TARGET_STRATEGY = "MEAN_REVERSION_ZSCORE_V1"
TARGET_SYMBOL = "SBER@MISX"
TARGET_TIMEFRAME = "M5"

SBER_LOT_SIZE = Decimal("10")
TOLERANCE = Decimal("0.05")


def dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def params_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if isinstance(value, str):
        return dict(json.loads(value))

    return {}


def implied_quantity(row: dict[str, Any]) -> Decimal | None:
    entry = dec(row["entry_price"])
    exit_ = dec(row["exit_price"])
    gross = abs(dec(row["gross_pnl"]))
    price_move = abs(exit_ - entry)

    if price_move == 0:
        return None

    return gross / price_move


def near(value: Decimal, expected: Decimal) -> bool:
    return abs(value - expected) <= TOLERANCE


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SBER Cost Replay Quantity Semantics V1"
    )
    parser.add_argument(
        "--batch-id",
        default=TARGET_BATCH,
    )
    args = parser.parse_args()

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                WITH ranked AS (
                    SELECT
                        r.run_uuid,
                        r.research_code,
                        r.parameter_hash,
                        r.parameter_json,
                        count(*)::bigint AS trades,
                        avg(
                            t.net_pnl + t.commission
                        )::numeric AS execution_expectancy,
                        row_number() OVER (
                            ORDER BY
                                avg(
                                    t.net_pnl + t.commission
                                ) DESC,
                                count(*) DESC,
                                r.run_uuid
                        ) AS rank_no
                    FROM analytics.edge_lab_run_v1 r
                    JOIN analytics.research_trade_v1 t
                      ON t.run_uuid = r.run_uuid
                    WHERE r.research_batch_id = %s
                      AND r.strategy_code = %s
                      AND r.symbol = %s
                      AND r.timeframe = %s
                    GROUP BY
                        r.run_uuid,
                        r.research_code,
                        r.parameter_hash,
                        r.parameter_json
                )
                SELECT *
                FROM ranked
                WHERE rank_no = 1
                """,
                (
                    args.batch_id,
                    TARGET_STRATEGY,
                    TARGET_SYMBOL,
                    TARGET_TIMEFRAME,
                ),
            )
            run = cur.fetchone()

            if run is None:
                raise SystemExit("ERROR=target_run_missing")

            cur.execute(
                """
                SELECT
                    trade_no,
                    side,
                    entry_price,
                    exit_price,
                    gross_pnl,
                    commission,
                    slippage,
                    net_pnl
                FROM analytics.research_trade_v1
                WHERE run_uuid = %s
                ORDER BY trade_no
                LIMIT 5000
                """,
                (run["run_uuid"],),
            )
            trades = [
                dict(row)
                for row in cur.fetchall()
            ]

    parameters = params_dict(run["parameter_json"])
    configured_quantity = dec(
        parameters.get("quantity", 0)
    )

    implied_values = [
        value
        for row in trades
        if (value := implied_quantity(row)) is not None
    ]

    if not implied_values:
        raise SystemExit(
            "ERROR=implied_quantity_not_calculable"
        )

    median_implied_quantity = Decimal(
        str(statistics.median(implied_values))
    )

    if near(median_implied_quantity, Decimal("1")):
        pnl_quantity_semantics = "ONE_PRICE_UNIT"
        executable_lot_replay_ready = 0
        block_reason = (
            "SOURCE_PNL_APPEARS_TO_USE_ONE_SHARE_NOT_ONE_SBER_LOT"
        )
    elif near(median_implied_quantity, SBER_LOT_SIZE):
        pnl_quantity_semantics = "ONE_SBER_LOT"
        executable_lot_replay_ready = 1
        block_reason = ""
    else:
        pnl_quantity_semantics = "UNRESOLVED"
        executable_lot_replay_ready = 0
        block_reason = (
            "IMPLIED_QUANTITY_DOES_NOT_MATCH_SHARE_OR_LOT"
        )

    print(f"source_run_uuid={run['run_uuid']}")
    print(f"research_code={run['research_code']}")
    print(f"parameter_hash={run['parameter_hash']}")
    print(f"trades={run['trades']}")
    print(
        "execution_expectancy="
        f"{run['execution_expectancy']}"
    )
    print(f"configured_quantity={configured_quantity}")
    print(
        "median_implied_quantity="
        f"{median_implied_quantity}"
    )
    print(f"sber_lot_size={SBER_LOT_SIZE}")
    print(
        "pnl_quantity_semantics="
        f"{pnl_quantity_semantics}"
    )
    print(
        "executable_lot_replay_ready="
        f"{executable_lot_replay_ready}"
    )
    print(f"block_reason={block_reason}")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")

    if executable_lot_replay_ready:
        print(
            "VERDICT="
            "SBER_COST_REPLAY_QUANTITY_SEMANTICS_V1_READY"
        )
        return 0

    print(
        "VERDICT="
        "SBER_COST_REPLAY_QUANTITY_SEMANTICS_V1_BLOCKED"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
