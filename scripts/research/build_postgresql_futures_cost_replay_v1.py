#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


SUPPORTED_SYMBOLS = {
    "BRM6@RTSX",
    "BRN6@RTSX",
    "NGK6@RTSX",
}


def dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def profit_factor(values: list[Decimal]) -> Decimal:
    gains = sum(
        (value for value in values if value > 0),
        Decimal("0"),
    )
    losses = abs(
        sum(
            (value for value in values if value < 0),
            Decimal("0"),
        )
    )

    if losses > 0:
        return gains / losses

    return gains if gains > 0 else Decimal("0")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PostgreSQL Futures Cost Replay V1"
    )
    parser.add_argument(
        "--source-run-uuid",
        required=True,
    )
    parser.add_argument(
        "--commission-per-contract-side",
        type=Decimal,
        required=True,
    )
    parser.add_argument(
        "--contracts-per-trade",
        type=Decimal,
        default=Decimal("1"),
    )
    parser.add_argument(
        "--cost-model-version",
        required=True,
    )
    args = parser.parse_args()

    if args.commission_per_contract_side < 0:
        raise SystemExit(
            "ERROR=commission_per_contract_side_negative"
        )

    if args.contracts_per_trade <= 0:
        raise SystemExit(
            "ERROR=contracts_per_trade_not_positive"
        )

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    research_batch_id,
                    research_code,
                    strategy_code,
                    strategy_version,
                    symbol,
                    timeframe,
                    parameter_hash,
                    parameter_json,
                    status_code
                FROM analytics.edge_lab_run_v1
                WHERE run_uuid = %s::uuid
                """,
                (args.source_run_uuid,),
            )
            run = cursor.fetchone()

            if run is None:
                raise SystemExit(
                    "ERROR=source_run_not_found"
                )

            if run["symbol"] not in SUPPORTED_SYMBOLS:
                raise SystemExit(
                    "ERROR=unsupported_symbol:"
                    f"{run['symbol']}"
                )

            cursor.execute(
                """
                SELECT
                    trade_no,
                    gross_pnl,
                    commission,
                    slippage,
                    net_pnl
                FROM analytics.research_trade_v1
                WHERE run_uuid = %s::uuid
                ORDER BY trade_no
                """,
                (args.source_run_uuid,),
            )

            trades = [
                dict(row)
                for row in cursor.fetchall()
            ]

    if not trades:
        raise SystemExit(
            "ERROR=source_trade_rows_missing"
        )

    round_trip_commission = (
        args.commission_per_contract_side
        * args.contracts_per_trade
        * Decimal("2")
    )

    replay_rows: list[dict[str, Decimal]] = []

    for trade in trades:
        gross_pnl = dec(trade["gross_pnl"])
        source_slippage = dec(trade["slippage"])

        replay_net_pnl = (
            gross_pnl
            - source_slippage
            - round_trip_commission
        )

        replay_rows.append(
            {
                "gross_pnl": gross_pnl,
                "slippage": source_slippage,
                "commission": round_trip_commission,
                "net_pnl": replay_net_pnl,
            }
        )

    trade_count = len(replay_rows)

    gross_sum = sum(
        (
            row["gross_pnl"]
            for row in replay_rows
        ),
        Decimal("0"),
    )
    slippage_sum = sum(
        (
            row["slippage"]
            for row in replay_rows
        ),
        Decimal("0"),
    )
    commission_sum = sum(
        (
            row["commission"]
            for row in replay_rows
        ),
        Decimal("0"),
    )

    net_values = [
        row["net_pnl"]
        for row in replay_rows
    ]
    net_sum = sum(net_values, Decimal("0"))

    wins = sum(value > 0 for value in net_values)
    losses = sum(value < 0 for value in net_values)

    expectancy = (
        net_sum / Decimal(trade_count)
    )
    pf = profit_factor(net_values)

    verdict = (
        "POSITIVE_AFTER_VERIFIED_FUTURES_COSTS"
        if expectancy > 0 and pf > 1
        else "NEGATIVE_AFTER_VERIFIED_FUTURES_COSTS"
    )

    print("=== POSTGRESQL FUTURES COST REPLAY V1 ===")
    print(f"source_run_uuid={run['run_uuid']}")
    print(f"research_batch_id={run['research_batch_id']}")
    print(f"research_code={run['research_code']}")
    print(f"strategy_code={run['strategy_code']}")
    print(f"strategy_version={run['strategy_version']}")
    print(f"symbol={run['symbol']}")
    print(f"timeframe={run['timeframe']}")
    print(f"parameter_hash={run['parameter_hash']}")
    print(f"cost_model_version={args.cost_model_version}")
    print(
        "commission_per_contract_side="
        f"{args.commission_per_contract_side}"
    )
    print(
        "contracts_per_trade="
        f"{args.contracts_per_trade}"
    )
    print(
        "round_trip_commission_per_trade="
        f"{round_trip_commission}"
    )
    print(f"trade_count={trade_count}")
    print(f"wins={wins}")
    print(f"losses={losses}")
    print(f"replay_gross_pnl={gross_sum}")
    print(f"replay_slippage={slippage_sum}")
    print(f"replay_commission={commission_sum}")
    print(f"replay_net_pnl={net_sum}")
    print(f"replay_expectancy={expectancy}")
    print(f"replay_profit_factor={pf}")
    print(f"verdict_code={verdict}")
    print("db_writes_performed=0")
    print("historical_trade_rows_changed=0")
    print("historical_observation_rows_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_FUTURES_COST_REPLAY_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
