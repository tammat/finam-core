#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.finam_commission_model_v1 import (
    MODEL_FINAM_EQUITY_REPORT_PROXY_V1,
    calculate_round_trip_commission,
)


TARGET_STRATEGY = "MEAN_REVERSION_ZSCORE_V1"
TARGET_SYMBOL = "SBER@MISX"
TARGET_TIMEFRAME = "M5"

DEFAULT_LOT_SIZE = Decimal("10")


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
        description=(
            "PostgreSQL Cost Replay Quantity Scaling V1"
        )
    )
    parser.add_argument(
        "--source-run-uuid",
        required=True,
    )
    parser.add_argument(
        "--lot-size",
        type=Decimal,
        default=DEFAULT_LOT_SIZE,
    )
    parser.add_argument(
        "--broker-order-fee-per-side",
        type=Decimal,
        default=Decimal("41.30"),
    )
    parser.add_argument(
        "--settlement-fee-rate",
        type=Decimal,
        default=Decimal("0.0003"),
    )
    parser.add_argument(
        "--exchange-fee-rate",
        type=Decimal,
        default=Decimal("0"),
    )
    parser.add_argument(
        "--other-fee-per-side",
        type=Decimal,
        default=Decimal("0"),
    )
    args = parser.parse_args()

    if args.lot_size <= 0:
        raise SystemExit("ERROR=lot_size_must_be_positive")

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    run_uuid::text,
                    strategy_code,
                    symbol,
                    timeframe,
                    parameter_hash,
                    parameter_json
                FROM analytics.edge_lab_run_v1
                WHERE run_uuid = %s::uuid
                """,
                (args.source_run_uuid,),
            )

            run = cur.fetchone()

            if run is None:
                raise SystemExit("ERROR=source_run_not_found")

            if run["strategy_code"] != TARGET_STRATEGY:
                raise SystemExit(
                    "ERROR=unexpected_strategy:"
                    f"{run['strategy_code']}"
                )

            if run["symbol"] != TARGET_SYMBOL:
                raise SystemExit(
                    f"ERROR=unexpected_symbol:{run['symbol']}"
                )

            if run["timeframe"] != TARGET_TIMEFRAME:
                raise SystemExit(
                    "ERROR=unexpected_timeframe:"
                    f"{run['timeframe']}"
                )

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
                WHERE run_uuid = %s::uuid
                ORDER BY trade_no
                """,
                (args.source_run_uuid,),
            )

            source_trades = [
                dict(row)
                for row in cur.fetchall()
            ]

    if not source_trades:
        raise SystemExit("ERROR=source_trade_rows_missing")

    replay_rows: list[dict[str, Decimal]] = []

    for trade in source_trades:
        source_gross = dec(trade["gross_pnl"])
        source_slippage = dec(trade["slippage"])

        replay_gross = source_gross * args.lot_size
        replay_slippage = source_slippage * args.lot_size

        commission = calculate_round_trip_commission(
            entry_price=dec(trade["entry_price"]),
            exit_price=dec(trade["exit_price"]),
            quantity_units=args.lot_size,
            parameters={
                "commission_model": (
                    MODEL_FINAM_EQUITY_REPORT_PROXY_V1
                ),
                "broker_order_fee_per_side": (
                    args.broker_order_fee_per_side
                ),
                "settlement_fee_rate": (
                    args.settlement_fee_rate
                ),
                "exchange_fee_rate": (
                    args.exchange_fee_rate
                ),
                "other_fee_per_side": (
                    args.other_fee_per_side
                ),
            },
        )

        replay_commission = commission.round_trip_total

        replay_net = (
            replay_gross
            - replay_slippage
            - replay_commission
        )

        replay_rows.append(
            {
                "replay_gross": replay_gross,
                "replay_slippage": replay_slippage,
                "replay_commission": replay_commission,
                "replay_net": replay_net,
            }
        )

    trades = len(replay_rows)

    gross_sum = sum(
        (
            row["replay_gross"]
            for row in replay_rows
        ),
        Decimal("0"),
    )

    slippage_sum = sum(
        (
            row["replay_slippage"]
            for row in replay_rows
        ),
        Decimal("0"),
    )

    commission_sum = sum(
        (
            row["replay_commission"]
            for row in replay_rows
        ),
        Decimal("0"),
    )

    net_values = [
        row["replay_net"]
        for row in replay_rows
    ]

    net_sum = sum(net_values, Decimal("0"))

    expectancy = net_sum / Decimal(trades)
    pf = profit_factor(net_values)

    wins = sum(value > 0 for value in net_values)
    losses = sum(value < 0 for value in net_values)

    win_rate = (
        Decimal(wins)
        / Decimal(trades)
        * Decimal("100")
    )

    verdict = (
        "POSITIVE_AFTER_QUANTITY_SCALED_COSTS"
        if expectancy > 0 and pf > 1
        else "NEGATIVE_AFTER_QUANTITY_SCALED_COSTS"
    )

    print(
        "=== POSTGRESQL COST REPLAY "
        "QUANTITY SCALING V1 ==="
    )
    print(f"source_run_uuid={args.source_run_uuid}")
    print(f"strategy_code={run['strategy_code']}")
    print(f"symbol={run['symbol']}")
    print(f"timeframe={run['timeframe']}")
    print(f"parameter_hash={run['parameter_hash']}")
    print(f"lot_size={args.lot_size}")
    print(f"source_trade_count={trades}")
    print(f"replay_gross_pnl={gross_sum}")
    print(f"replay_slippage={slippage_sum}")
    print(f"replay_commission={commission_sum}")
    print(f"replay_net_pnl={net_sum}")
    print(f"replay_expectancy={expectancy}")
    print(f"replay_profit_factor={pf}")
    print(f"replay_wins={wins}")
    print(f"replay_losses={losses}")
    print(f"replay_win_rate={win_rate}")
    print(f"verdict_code={verdict}")
    print("quantity_scaling_applied=1")
    print("gross_pnl_scaled=1")
    print("slippage_scaled=1")
    print("commission_recalculated=1")
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
        "POSTGRESQL_COST_REPLAY_QUANTITY_SCALING_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
