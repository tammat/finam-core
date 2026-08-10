from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from marketcore.research.economics.legacy_strategy_runner_cost_replay_v1 import (
    LegacyStrategyRunnerCostContractV1,
    resolve_legacy_strategy_runner_cost_v1,
)


D = Decimal

RUN_UUID = "b3de8690-eedc-4831-88eb-2b32f567bc81"

CONTRACT = LegacyStrategyRunnerCostContractV1(
    commission_per_trade=D("0.01"),
    commission_pct=D("0.0005"),
    slippage_per_trade=D("0.01"),
)

TOLERANCE = D("0.00000001")


def dec(value) -> Decimal:
    return D(str(value))


def main() -> int:
    rows_checked = 0
    commission_matches = 0
    slippage_matches = 0
    net_matches = 0

    replay_commission = D("0")
    replay_slippage = D("0")
    replay_net = D("0")

    persisted_commission = D("0")
    persisted_slippage = D("0")
    persisted_net = D("0")

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

    for row in rows:
        gross = dec(row["gross_pnl"])

        cost = resolve_legacy_strategy_runner_cost_v1(
            entry_price=dec(row["entry_price"]),
            contract=CONTRACT,
        )

        calculated_net = (
            gross
            - cost.commission
            - cost.slippage
        )

        stored_commission = dec(
            row["commission"]
        )
        stored_slippage = dec(
            row["slippage"]
        )
        stored_net = dec(
            row["net_pnl"]
        )

        commission_match = (
            abs(
                cost.commission
                - stored_commission
            )
            <= TOLERANCE
        )

        slippage_match = (
            abs(
                cost.slippage
                - stored_slippage
            )
            <= TOLERANCE
        )

        net_match = (
            abs(
                calculated_net
                - stored_net
            )
            <= TOLERANCE
        )

        rows_checked += 1
        commission_matches += int(
            commission_match
        )
        slippage_matches += int(
            slippage_match
        )
        net_matches += int(net_match)

        replay_commission += cost.commission
        replay_slippage += cost.slippage
        replay_net += calculated_net

        persisted_commission += (
            stored_commission
        )
        persisted_slippage += stored_slippage
        persisted_net += stored_net

    print(f"rows_checked={rows_checked}")
    print(
        f"commission_matches="
        f"{commission_matches}"
    )
    print(
        f"slippage_matches="
        f"{slippage_matches}"
    )
    print(f"net_matches={net_matches}")

    print(
        f"replay_commission="
        f"{replay_commission}"
    )
    print(
        f"persisted_commission="
        f"{persisted_commission}"
    )

    print(
        f"replay_slippage="
        f"{replay_slippage}"
    )
    print(
        f"persisted_slippage="
        f"{persisted_slippage}"
    )

    print(f"replay_net_pnl={replay_net}")
    print(
        f"persisted_net_pnl="
        f"{persisted_net}"
    )

    if rows_checked != 550:
        raise RuntimeError(
            "ERROR=V1_TRADE_COUNT_MISMATCH"
        )

    if commission_matches != rows_checked:
        raise RuntimeError(
            "ERROR=COMMISSION_SEMANTICS_MISMATCH"
        )

    if slippage_matches != rows_checked:
        raise RuntimeError(
            "ERROR=SLIPPAGE_SEMANTICS_MISMATCH"
        )

    if net_matches != rows_checked:
        raise RuntimeError(
            "ERROR=NET_SEMANTICS_MISMATCH"
        )

    print("quantity_unit=1")
    print(
        "commission_semantics="
        "ENTRY_PRICE_PCT_PLUS_FIXED_PER_TRADE"
    )
    print(
        "slippage_semantics="
        "FIXED_PER_TRADE_TOTAL"
    )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "LKOH_RUNNER_V1_COST_SEMANTICS_"
        "VALIDATION_V1_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
