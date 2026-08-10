from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import psycopg2

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)
from marketcore.research.net_first_shadow_admission_v1 import (
    evaluate_shadow_admission_v1,
)


D = Decimal

POLICY = EconomicCostGatePolicyV1(
    minimum_trades=50,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)

POLICY_VERSION = "ECONOMIC_COST_GATE_POLICY_V1"
SOURCE_VERSION = "NET_FIRST_SHADOW_OBSERVER_V1"

CASES = (
    {
        "candidate_code": "TREND_PULLBACK_V1:NVTK@MISX:M5",
        "symbol": "NVTK@MISX",
        "strategy_code": "TREND_PULLBACK_V1",
        "timeframe": "M5",
        "trades": 1153,
        "gross_pnl": D("456.1"),
        "total_cost": D("1236.708750000"),
        "cost_contract_version": "COMMISSION_MODEL_V1",
        "actual_robustness_scheduled": True,
    },
    {
        "candidate_code": "TREND_PULLBACK_V1:PLZL@MISX:M5",
        "symbol": "PLZL@MISX",
        "strategy_code": "TREND_PULLBACK_V1",
        "timeframe": "M5",
        "trades": 1121,
        "gross_pnl": D("1034.0"),
        "total_cost": D("2057.080000000"),
        "cost_contract_version": "COMMISSION_MODEL_V1",
        "actual_robustness_scheduled": True,
    },
    {
        "candidate_code": "TREND_PULLBACK_V1:USDRUBF@RTSX:M5",
        "symbol": "USDRUBF@RTSX",
        "strategy_code": "TREND_PULLBACK_V1",
        "timeframe": "M5",
        "trades": 2573,
        "gross_pnl": D("23195.0"),
        "total_cost": D("23528.514073"),
        "cost_contract_version": "USDRUBF_FUTURES_COST_SEMANTICS_V1",
        "actual_robustness_scheduled": True,
    },
)


def build_rows(case):
    gross_per_trade = (
        case["gross_pnl"]
        / D(case["trades"])
    )

    cost_per_trade = (
        case["total_cost"]
        / D(case["trades"])
    )

    return tuple(
        CanonicalEconomicTradeInputV1(
            gross_pnl=gross_per_trade,
            commission=cost_per_trade,
            slippage=D("0"),
        )
        for _ in range(case["trades"])
    )


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")

    if not dsn:
        raise SystemExit(
            "ERROR=DATABASE_URL_NOT_SET"
        )

    inserted = 0
    would_reject = 0
    would_admit = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            for case in CASES:
                result = evaluate_shadow_admission_v1(
                    economic_trades=build_rows(case),
                    policy=POLICY,
                )

                economic = result.economic_result

                cur.execute(
                    """
                    INSERT INTO analytics.net_first_shadow_admission_v1 (
                        observation_uuid,
                        candidate_code,
                        symbol,
                        strategy_code,
                        timeframe,
                        canonical_trades,
                        gross_pnl,
                        total_cost,
                        net_pnl,
                        net_expectancy,
                        net_profit_factor,
                        economic_gate_status,
                        shadow_decision,
                        actual_robustness_scheduled,
                        production_blocked,
                        cost_contract_version,
                        policy_version,
                        source_version
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s
                    )
                    """,
                    (
                        str(uuid4()),
                        case["candidate_code"],
                        case["symbol"],
                        case["strategy_code"],
                        case["timeframe"],
                        economic.trades,
                        economic.gross_pnl,
                        economic.total_cost,
                        economic.net_pnl,
                        economic.net_expectancy,
                        economic.net_profit_factor,
                        str(economic.status),
                        str(result.decision),
                        case["actual_robustness_scheduled"],
                        result.production_blocked,
                        case["cost_contract_version"],
                        POLICY_VERSION,
                        SOURCE_VERSION,
                    ),
                )

                inserted += 1
                would_reject += int(
                    str(result.decision) == "WOULD_REJECT"
                )
                would_admit += int(
                    str(result.decision) == "WOULD_ADMIT"
                )

                print(
                    "SHADOW_OBSERVATION_ROW "
                    f"symbol={case['symbol']} "
                    f"decision={result.decision} "
                    f"economic_status={economic.status} "
                    f"net_pnl={economic.net_pnl} "
                    f"production_blocked="
                    f"{int(result.production_blocked)}"
                )

        conn.commit()

    print(f"rows_inserted={inserted}")
    print(f"would_reject={would_reject}")
    print(f"would_admit={would_admit}")
    print("shadow_admission_enabled=1")
    print("enforced_admission_enabled=0")
    print("production_pipeline_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "NET_FIRST_SHADOW_OBSERVER_V1_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
