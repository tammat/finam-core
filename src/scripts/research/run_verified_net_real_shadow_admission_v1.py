from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)
from marketcore.research.economics.economic_evidence_classifier_v1 import (
    EconomicEvidenceClassV1,
    classify_economic_evidence_v1,
)
from marketcore.research.economics.verified_net_admission_v1 import (
    VerifiedNetMetricsV1,
    evaluate_verified_net_admission_v1,
)


D = Decimal

POLICY = EconomicCostGatePolicyV1(
    minimum_trades=50,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)


def dec(value) -> Decimal:
    return D(str(value or 0))


def main() -> int:
    cohort = 0
    would_admit = 0
    would_reject = 0
    oos_fail = 0

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
                    c.observation_uuid,
                    c.discovery_batch_id,
                    c.strategy_code,
                    c.symbol,
                    c.timeframe,
                    c.parameter_hash,

                    o.trades,
                    o.profit_factor,
                    o.expectancy,
                    o.commission,
                    o.slippage,
                    o.verdict_code,
                    o.runner_version,
                    o.score_formula_version,
                    o.source_version,

                    x.verdict_code AS oos_verdict

                FROM analytics.edge_candidate_v1 c

                JOIN analytics.edge_observation_v1 o
                  ON o.observation_uuid =
                     c.observation_uuid

                LEFT JOIN analytics.edge_oos_result_v1 x
                  ON x.observation_uuid =
                     c.observation_uuid

                ORDER BY c.observation_uuid
                """
            )

            rows = cur.fetchall()

    for row in rows:
        evidence = classify_economic_evidence_v1(
            runner_version=str(
                row["runner_version"]
            ),
            score_formula_version=str(
                row["score_formula_version"]
            ),
            source_version=str(
                row["source_version"]
            ),
            verdict_code=str(
                row["verdict_code"]
            ),
            commission=dec(
                row["commission"]
            ),
            slippage=dec(
                row["slippage"]
            ),
        )

        if (
            evidence.evidence_class
            != EconomicEvidenceClassV1
            .VERIFIED_NET_METRICS
        ):
            continue

        result = evaluate_verified_net_admission_v1(
            metrics=VerifiedNetMetricsV1(
                trades=int(row["trades"]),
                net_profit_factor=dec(
                    row["profit_factor"]
                ),
                net_expectancy=dec(
                    row["expectancy"]
                ),
            ),
            policy=POLICY,
        )

        decision = (
            "WOULD_ADMIT"
            if result.passed
            else "WOULD_REJECT"
        )

        cohort += 1
        would_admit += int(result.passed)
        would_reject += int(
            not result.passed
        )
        oos_fail += int(
            row["oos_verdict"] == "OOS_FAIL"
        )

        print(
            "REAL_VERIFIED_NET_SHADOW_ROW "
            f"observation_uuid="
            f"{row['observation_uuid']} "
            f"strategy={row['strategy_code']} "
            f"symbol={row['symbol']} "
            f"trades={row['trades']} "
            f"net_pf={row['profit_factor']} "
            f"net_expectancy="
            f"{row['expectancy']} "
            f"decision={decision} "
            f"economic_status="
            f"{result.status} "
            f"oos_verdict="
            f"{row['oos_verdict']}"
        )

    print(
        f"verified_net_candidates={cohort}"
    )
    print(f"would_admit={would_admit}")
    print(f"would_reject={would_reject}")
    print(f"oos_fail={oos_fail}")

    print("aggregate_net_metrics_used=1")
    print("synthetic_trade_reconstruction_used=0")
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
        "VERIFIED_NET_REAL_SHADOW_ADMISSION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
