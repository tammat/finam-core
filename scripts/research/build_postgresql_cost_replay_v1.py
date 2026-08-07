#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

import psycopg2
from psycopg2.extras import RealDictCursor, Json

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.finam_commission_model_v1 import (
    MODEL_FINAM_EQUITY_REPORT_PROXY_V1,
    MODEL_FINAM_FUTURES_CONFIGURED_V1,
    MODEL_LEGACY_FIXED_PER_SIDE,
    calculate_round_trip_commission,
)


MODEL_FINAM_FUTURES_ALLOCATED_V1 = (
    "FINAM_FUTURES_ALLOCATED_V1"
)

SUPPORTED_REPLAY_MODELS = {
    MODEL_LEGACY_FIXED_PER_SIDE,
    MODEL_FINAM_EQUITY_REPORT_PROXY_V1,
    MODEL_FINAM_FUTURES_ALLOCATED_V1,
}


class ReplayBlockedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CostResult:
    broker_fee: Decimal
    exchange_fee: Decimal
    clearing_fee: Decimal
    other_fee: Decimal
    total_commission: Decimal
    evidence_status: str
    evidence_reference: str


def dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def parameters_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        return dict(json.loads(value))
    return {}


def is_futures_symbol(symbol: str) -> bool:
    return symbol.endswith("@RTSX")


def load_source_run(
    cursor: RealDictCursor,
    source_run_uuid: str,
) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT
            run_uuid::text,
            research_batch_id,
            strategy_code,
            strategy_version,
            symbol,
            timeframe,
            parameter_hash,
            parameter_json,
            runner_version,
            source_version
        FROM analytics.edge_lab_run_v1
        WHERE run_uuid = %s::uuid
        """,
        (source_run_uuid,),
    )
    row = cursor.fetchone()

    if row is None:
        raise RuntimeError(
            f"source_run_not_found:{source_run_uuid}"
        )

    return dict(row)


def load_source_trades(
    cursor: RealDictCursor,
    source_run_uuid: str,
) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            trade_no,
            side,
            entry_ts,
            exit_ts,
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
        (source_run_uuid,),
    )
    return [dict(row) for row in cursor.fetchall()]


def load_futures_allocation(
    cursor: RealDictCursor,
    *,
    symbol: str,
    trade_date: Any,
    model_version: str,
) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT
            trade_date,
            symbol,
            allocation_model,
            allocated_commission,
            contracts,
            commission_per_contract,
            source_document,
            source_version
        FROM analytics.futures_commission_allocation_v1
        WHERE trade_date = %s
          AND symbol = %s
          AND allocation_model = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (
            trade_date,
            symbol,
            model_version,
        ),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def calculate_cost(
    cursor: RealDictCursor,
    *,
    model_code: str,
    model_parameters: Mapping[str, Any],
    symbol: str,
    trade: Mapping[str, Any],
    quantity: Decimal,
) -> CostResult:
    entry_price = dec(trade["entry_price"])
    exit_price = dec(trade["exit_price"])

    if model_code == MODEL_LEGACY_FIXED_PER_SIDE:
        breakdown = calculate_round_trip_commission(
            entry_price=entry_price,
            exit_price=exit_price,
            quantity_units=quantity,
            parameters={
                **model_parameters,
                "commission_model": (
                    MODEL_LEGACY_FIXED_PER_SIDE
                ),
            },
        )

        return CostResult(
            broker_fee=breakdown.round_trip_total,
            exchange_fee=Decimal("0"),
            clearing_fee=Decimal("0"),
            other_fee=Decimal("0"),
            total_commission=breakdown.round_trip_total,
            evidence_status="STORED",
            evidence_reference="LEGACY_PARAMETER_MODEL",
        )

    if model_code == MODEL_FINAM_EQUITY_REPORT_PROXY_V1:
        if is_futures_symbol(symbol):
            raise ReplayBlockedError(
                "equity_cost_model_not_allowed_for_futures"
            )

        breakdown = calculate_round_trip_commission(
            entry_price=entry_price,
            exit_price=exit_price,
            quantity_units=quantity,
            parameters={
                **model_parameters,
                "commission_model": (
                    MODEL_FINAM_EQUITY_REPORT_PROXY_V1
                ),
            },
        )

        broker_fee = (
            breakdown.entry_broker_fee
            + breakdown.exit_broker_fee
        )
        exchange_fee = (
            breakdown.entry_exchange_fee
            + breakdown.exit_exchange_fee
        )
        clearing_fee = (
            breakdown.entry_settlement_fee
            + breakdown.exit_settlement_fee
        )
        other_fee = (
            breakdown.entry_other_fee
            + breakdown.exit_other_fee
        )

        return CostResult(
            broker_fee=broker_fee,
            exchange_fee=exchange_fee,
            clearing_fee=clearing_fee,
            other_fee=other_fee,
            total_commission=breakdown.round_trip_total,
            evidence_status="PROXY",
            evidence_reference=(
                "FINAM_ACTUAL_COMMISSION_SIDE_EVIDENCE_V1"
            ),
        )

    if model_code == MODEL_FINAM_FUTURES_ALLOCATED_V1:
        if not is_futures_symbol(symbol):
            raise ReplayBlockedError(
                "futures_cost_model_not_allowed_for_equity"
            )

        allocation_model = str(
            model_parameters.get(
                "futures_allocation_model",
                "CONTRACT_COUNT",
            )
        )

        entry_allocation = load_futures_allocation(
            cursor,
            symbol=symbol,
            trade_date=trade["entry_ts"].date(),
            model_version=allocation_model,
        )
        exit_allocation = load_futures_allocation(
            cursor,
            symbol=symbol,
            trade_date=trade["exit_ts"].date(),
            model_version=allocation_model,
        )

        if entry_allocation is None:
            raise ReplayBlockedError(
                "entry_futures_commission_allocation_missing:"
                f"{trade['entry_ts'].date()}:{symbol}"
            )

        if exit_allocation is None:
            raise ReplayBlockedError(
                "exit_futures_commission_allocation_missing:"
                f"{trade['exit_ts'].date()}:{symbol}"
            )

        entry_cost = (
            dec(entry_allocation["commission_per_contract"])
            * quantity
        )
        exit_cost = (
            dec(exit_allocation["commission_per_contract"])
            * quantity
        )
        total = entry_cost + exit_cost

        references = (
            f"{entry_allocation['source_document']}:"
            f"{entry_allocation['source_version']};"
            f"{exit_allocation['source_document']}:"
            f"{exit_allocation['source_version']}"
        )

        return CostResult(
            broker_fee=total,
            exchange_fee=Decimal("0"),
            clearing_fee=Decimal("0"),
            other_fee=Decimal("0"),
            total_commission=total,
            evidence_status="VERIFIED",
            evidence_reference=references,
        )

    raise RuntimeError(
        f"unsupported_replay_cost_model:{model_code}"
    )


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
        description="PostgreSQL Cost Replay V1"
    )
    parser.add_argument(
        "--source-run-uuid",
        required=True,
    )
    parser.add_argument(
        "--cost-model",
        required=True,
        choices=sorted(SUPPORTED_REPLAY_MODELS),
    )
    parser.add_argument(
        "--cost-model-version",
        required=True,
    )
    parser.add_argument(
        "--quantity",
        type=Decimal,
        default=Decimal("1"),
    )
    parser.add_argument(
        "--commission-per-side",
        type=Decimal,
        default=Decimal("1.5"),
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
    parser.add_argument(
        "--futures-allocation-model",
        default="CONTRACT_COUNT",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    args = parser.parse_args()

    if args.quantity <= 0:
        raise SystemExit("ERROR=quantity_must_be_positive")

    replay_uuid = str(uuid.uuid4())

    replay_parameters = {
        "quantity": str(args.quantity),
        "commission_per_side": str(
            args.commission_per_side
        ),
        "broker_order_fee_per_side": str(
            args.broker_order_fee_per_side
        ),
        "settlement_fee_rate": str(
            args.settlement_fee_rate
        ),
        "exchange_fee_rate": str(
            args.exchange_fee_rate
        ),
        "other_fee_per_side": str(
            args.other_fee_per_side
        ),
        "futures_allocation_model": (
            args.futures_allocation_model
        ),
    }

    with psycopg2.connect(build_psycopg_url()) as conn:
        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            source_run = load_source_run(
                cursor,
                args.source_run_uuid,
            )
            source_trades = load_source_trades(
                cursor,
                args.source_run_uuid,
            )

            if not source_trades:
                raise SystemExit(
                    "ERROR=source_trade_rows_missing"
                )

            replay_rows: list[dict[str, Any]] = []

            try:
                for trade in source_trades:
                    cost = calculate_cost(
                        cursor,
                        model_code=args.cost_model,
                        model_parameters=replay_parameters,
                        symbol=str(source_run["symbol"]),
                        trade=trade,
                        quantity=args.quantity,
                    )

                    gross_pnl = dec(trade["gross_pnl"])
                    slippage = dec(trade["slippage"])
                    replay_net_pnl = (
                        gross_pnl
                        - cost.total_commission
                        - slippage
                    )

                    replay_rows.append(
                        {
                            **trade,
                            "gross_pnl": gross_pnl,
                            "source_commission": dec(
                                trade["commission"]
                            ),
                            "source_slippage": slippage,
                            "source_net_pnl": dec(
                                trade["net_pnl"]
                            ),
                            "replay_broker_fee": (
                                cost.broker_fee
                            ),
                            "replay_exchange_fee": (
                                cost.exchange_fee
                            ),
                            "replay_clearing_fee": (
                                cost.clearing_fee
                            ),
                            "replay_other_fee": (
                                cost.other_fee
                            ),
                            "replay_commission": (
                                cost.total_commission
                            ),
                            "replay_net_pnl": (
                                replay_net_pnl
                            ),
                            "evidence_status": (
                                cost.evidence_status
                            ),
                            "evidence_reference": (
                                cost.evidence_reference
                            ),
                        }
                    )
            except ReplayBlockedError as error:
                if not args.dry_run:
                    cursor.execute(
                        """
                        INSERT INTO analytics.cost_replay_run_v1 (
                            replay_uuid,
                            source_run_uuid,
                            research_batch_id,
                            strategy_code,
                            strategy_version,
                            symbol,
                            timeframe,
                            parameter_hash,
                            source_cost_model_version,
                            replay_cost_model_version,
                            replay_parameters,
                            status_code,
                            failure_reason,
                            source_trade_count,
                            replay_trade_count,
                            started_at,
                            finished_at
                        )
                        VALUES (
                            %s::uuid,
                            %s::uuid,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            'BLOCKED',
                            %s,
                            %s,
                            0,
                            now(),
                            now()
                        )
                        ON CONFLICT (
                            source_run_uuid,
                            replay_cost_model_version
                        )
                        DO UPDATE SET
                            status_code = 'BLOCKED',
                            failure_reason = EXCLUDED.failure_reason,
                            finished_at = now()
                        """,
                        (
                            replay_uuid,
                            args.source_run_uuid,
                            source_run["research_batch_id"],
                            source_run["strategy_code"],
                            source_run["strategy_version"],
                            source_run["symbol"],
                            source_run["timeframe"],
                            source_run["parameter_hash"],
                            str(source_run["source_version"]),
                            args.cost_model_version,
                            Json(replay_parameters),
                            str(error),
                            len(source_trades),
                        ),
                    )

                print(f"source_run_uuid={args.source_run_uuid}")
                print(f"replay_cost_model={args.cost_model}")
                print(f"blocked_reason={error}")
                print(
                    f"db_writes_performed="
                    f"{0 if args.dry_run else 1}"
                )
                print("runtime_changed=0")
                print("execution_changed=0")
                print("orders_changed=0")
                print("fills_changed=0")
                print("micro_live_allowed=0")
                print(
                    "VERDICT="
                    "POSTGRESQL_COST_REPLAY_V1_BLOCKED"
                )
                return 2

            net_values = [
                dec(row["replay_net_pnl"])
                for row in replay_rows
            ]

            trades = len(replay_rows)
            wins = sum(value > 0 for value in net_values)
            losses = sum(value < 0 for value in net_values)

            gross_pnl_sum = sum(
                (
                    dec(row["gross_pnl"])
                    for row in replay_rows
                ),
                Decimal("0"),
            )
            source_commission_sum = sum(
                (
                    dec(row["source_commission"])
                    for row in replay_rows
                ),
                Decimal("0"),
            )
            replay_commission_sum = sum(
                (
                    dec(row["replay_commission"])
                    for row in replay_rows
                ),
                Decimal("0"),
            )
            replay_slippage_sum = sum(
                (
                    dec(row["source_slippage"])
                    for row in replay_rows
                ),
                Decimal("0"),
            )
            source_net_sum = sum(
                (
                    dec(row["source_net_pnl"])
                    for row in replay_rows
                ),
                Decimal("0"),
            )
            replay_net_sum = sum(
                net_values,
                Decimal("0"),
            )

            expectancy = (
                replay_net_sum / Decimal(trades)
            )
            pf = profit_factor(net_values)
            win_rate = (
                Decimal(wins)
                / Decimal(trades)
                * Decimal("100")
            )

            if expectancy > 0 and pf > 1:
                verdict = "POSITIVE_AFTER_REPLAY_COSTS"
            else:
                verdict = "NEGATIVE_AFTER_REPLAY_COSTS"

            evidence_statuses = {
                str(row["evidence_status"])
                for row in replay_rows
            }

            aggregate_evidence_status = (
                next(iter(evidence_statuses))
                if len(evidence_statuses) == 1
                else "MIXED"
            )

            if args.dry_run:
                print(f"replay_uuid={replay_uuid}")
                print(f"source_run_uuid={args.source_run_uuid}")
                print(f"symbol={source_run['symbol']}")
                print(f"trades={trades}")
                print(
                    f"source_commission="
                    f"{source_commission_sum}"
                )
                print(
                    f"replay_commission="
                    f"{replay_commission_sum}"
                )
                print(f"replay_net_pnl={replay_net_sum}")
                print(f"replay_expectancy={expectancy}")
                print(f"replay_profit_factor={pf}")
                print(f"verdict_code={verdict}")
                print("db_writes_performed=0")
                print(
                    "VERDICT="
                    "POSTGRESQL_COST_REPLAY_V1_DRY_RUN_OK"
                )
                return 0

            cursor.execute(
                """
                INSERT INTO analytics.cost_replay_run_v1 (
                    replay_uuid,
                    source_run_uuid,
                    research_batch_id,
                    strategy_code,
                    strategy_version,
                    symbol,
                    timeframe,
                    parameter_hash,
                    source_cost_model_version,
                    replay_cost_model_version,
                    replay_parameters,
                    status_code,
                    failure_reason,
                    source_trade_count,
                    replay_trade_count,
                    started_at,
                    finished_at
                )
                VALUES (
                    %s::uuid,
                    %s::uuid,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'RUNNING',
                    '',
                    %s,
                    0,
                    now(),
                    NULL
                )
                RETURNING replay_uuid::text
                """,
                (
                    replay_uuid,
                    args.source_run_uuid,
                    source_run["research_batch_id"],
                    source_run["strategy_code"],
                    source_run["strategy_version"],
                    source_run["symbol"],
                    source_run["timeframe"],
                    source_run["parameter_hash"],
                    str(source_run["source_version"]),
                    args.cost_model_version,
                    Json(replay_parameters),
                    trades,
                ),
            )

            replay_uuid = str(
                cursor.fetchone()["replay_uuid"]
            )

            for row in replay_rows:
                cursor.execute(
                    """
                    INSERT INTO analytics.cost_replay_trade_v1 (
                        replay_uuid,
                        source_run_uuid,
                        source_trade_no,
                        strategy_code,
                        symbol,
                        timeframe,
                        side,
                        entry_ts,
                        exit_ts,
                        entry_price,
                        exit_price,
                        quantity,
                        source_gross_pnl,
                        source_commission,
                        source_slippage,
                        source_net_pnl,
                        replay_broker_fee,
                        replay_exchange_fee,
                        replay_clearing_fee,
                        replay_other_fee,
                        replay_commission,
                        replay_slippage,
                        replay_net_pnl,
                        cost_model_version,
                        cost_evidence_status,
                        cost_evidence_reference
                    )
                    VALUES (
                        %s::uuid,
                        %s::uuid,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        replay_uuid,
                        args.source_run_uuid,
                        row["trade_no"],
                        source_run["strategy_code"],
                        source_run["symbol"],
                        source_run["timeframe"],
                        row["side"],
                        row["entry_ts"],
                        row["exit_ts"],
                        row["entry_price"],
                        row["exit_price"],
                        args.quantity,
                        row["gross_pnl"],
                        row["source_commission"],
                        row["source_slippage"],
                        row["source_net_pnl"],
                        row["replay_broker_fee"],
                        row["replay_exchange_fee"],
                        row["replay_clearing_fee"],
                        row["replay_other_fee"],
                        row["replay_commission"],
                        row["source_slippage"],
                        row["replay_net_pnl"],
                        args.cost_model_version,
                        row["evidence_status"],
                        row["evidence_reference"],
                    ),
                )

            cursor.execute(
                """
                INSERT INTO analytics.cost_replay_result_v1 (
                    replay_uuid,
                    source_run_uuid,
                    strategy_code,
                    symbol,
                    timeframe,
                    trades,
                    wins,
                    losses,
                    win_rate,
                    gross_pnl,
                    source_commission,
                    replay_commission,
                    replay_slippage,
                    replay_net_pnl,
                    replay_expectancy,
                    replay_profit_factor,
                    cost_delta,
                    net_pnl_delta,
                    verdict_code,
                    cost_model_version,
                    cost_evidence_status
                )
                VALUES (
                    %s::uuid,
                    %s::uuid,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    replay_uuid,
                    args.source_run_uuid,
                    source_run["strategy_code"],
                    source_run["symbol"],
                    source_run["timeframe"],
                    trades,
                    wins,
                    losses,
                    win_rate,
                    gross_pnl_sum,
                    source_commission_sum,
                    replay_commission_sum,
                    replay_slippage_sum,
                    replay_net_sum,
                    expectancy,
                    pf,
                    (
                        replay_commission_sum
                        - source_commission_sum
                    ),
                    replay_net_sum - source_net_sum,
                    verdict,
                    args.cost_model_version,
                    aggregate_evidence_status,
                ),
            )

            cursor.execute(
                """
                UPDATE analytics.cost_replay_run_v1
                SET
                    status_code = 'DONE',
                    replay_trade_count = %s,
                    finished_at = now()
                WHERE replay_uuid = %s::uuid
                """,
                (
                    trades,
                    replay_uuid,
                ),
            )

    print(f"replay_uuid={replay_uuid}")
    print(f"source_run_uuid={args.source_run_uuid}")
    print(f"symbol={source_run['symbol']}")
    print(f"trades={trades}")
    print(f"source_commission={source_commission_sum}")
    print(f"replay_commission={replay_commission_sum}")
    print(f"replay_net_pnl={replay_net_sum}")
    print(f"replay_expectancy={expectancy}")
    print(f"replay_profit_factor={pf}")
    print(f"verdict_code={verdict}")
    print("db_writes_performed=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=POSTGRESQL_COST_REPLAY_V1_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
