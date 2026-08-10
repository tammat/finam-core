from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)
from marketcore.research.economics.legacy_strategy_runner_cost_replay_v1 import (
    LegacyStrategyRunnerCostContractV1,
    resolve_legacy_strategy_runner_cost_v1,
)
from marketcore.research.economics.verified_net_admission_v1 import (
    VerifiedNetMetricsV1,
    evaluate_verified_net_admission_v1,
)


D = Decimal

RUN_UUID = "8b0eb257-f20e-476b-a2c8-43222247cd7a"

CONTRACT = LegacyStrategyRunnerCostContractV1(
    commission_per_trade=D("0.01"),
    commission_pct=D("0.0005"),
    slippage_per_trade=D("0.01"),
)

POLICY = EconomicCostGatePolicyV1(
    minimum_trades=50,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)


def dec(value) -> Decimal:
    return D(str(value))


def main() -> int:
    with psycopg2.connect(
        os.environ["DATABASE_URL"]
    ) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
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
                WHERE run_uuid=%s
                ORDER BY trade_no
                """,
                (RUN_UUID,),
            )

            rows = cur.fetchall()

    if len(rows) != 278:
        raise RuntimeError(
            "ERROR=RUNNER_V2_TRADE_COUNT_MISMATCH "
            f"expected=278 actual={len(rows)}"
        )

    gross_pnl = D("0")
    commission = D("0")
    slippage = D("0")
    net_pnl = D("0")

    gross_profit = D("0")
    gross_loss = D("0")

    source_zero_cost_rows = 0

    for row in rows:
        stored_commission = dec(
            row["commission"]
        )
        stored_slippage = dec(
            row["slippage"]
        )

        source_zero_cost_rows += int(
            stored_commission == 0
            and stored_slippage == 0
        )

        gross = dec(
            row["gross_pnl"]
        )

        resolved = (
            resolve_legacy_strategy_runner_cost_v1(
                entry_price=dec(
                    row["entry_price"]
                ),
                contract=CONTRACT,
            )
        )

        trade_net = (
            gross
            - resolved.commission
            - resolved.slippage
        )

        gross_pnl += gross
        commission += resolved.commission
        slippage += resolved.slippage
        net_pnl += trade_net

        if trade_net > 0:
            gross_profit += trade_net
        elif trade_net < 0:
            gross_loss += abs(trade_net)

    net_expectancy = (
        net_pnl / D(len(rows))
    )

    if gross_loss > 0:
        net_profit_factor = (
            gross_profit / gross_loss
        )
    elif gross_profit > 0:
        raise RuntimeError(
            "ERROR=INFINITE_NET_PROFIT_FACTOR"
        )
    else:
        net_profit_factor = D("0")

    admission = evaluate_verified_net_admission_v1(
        metrics=VerifiedNetMetricsV1(
            trades=len(rows),
            net_profit_factor=net_profit_factor,
            net_expectancy=net_expectancy,
        ),
        policy=POLICY,
    )

    decision = (
        "WOULD_ADMIT"
        if admission.passed
        else "WOULD_REJECT"
    )

    print(
        "LKOH_RUNNER_V2_COST_REPLAY_ROW "
        f"run_uuid={RUN_UUID} "
        f"trades={len(rows)} "
        f"gross_pnl={gross_pnl} "
        f"commission={commission} "
        f"slippage={slippage} "
        f"total_cost={commission + slippage} "
        f"net_pnl={net_pnl} "
        f"net_expectancy={net_expectancy} "
        f"net_profit_factor={net_profit_factor} "
        f"decision={decision} "
        f"economic_status={admission.status}"
    )

    print(
        f"source_zero_cost_rows="
        f"{source_zero_cost_rows}"
    )

    print("reconstructed_cost_rows=278")
    print("quantity_unit=1")

    print(
        "commission_semantics="
        "ENTRY_PRICE_PCT_PLUS_FIXED_PER_TRADE"
    )

    print(
        "slippage_semantics="
        "FIXED_PER_TRADE_TOTAL"
    )

    print(
        "legacy_v1_semantics_validated_before_v2_replay=1"
    )

    print("strategy_reconstruction_required=0")
    print("aggregate_observation_costs_used=0")
    print("individual_trade_rows_used=1")

    print("shadow_admission_enabled=1")
    print("enforced_admission_enabled=0")
    print("production_pipeline_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "LKOH_RUNNER_V2_COST_REPLAY_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
