from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
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


def main() -> int:
    candidates = 0
    would_admit = 0
    would_reject = 0

    with psycopg2.connect(
        os.environ["DATABASE_URL"]
    ) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                WITH agg AS (
                    SELECT
                        c.observation_uuid,
                        c.strategy_code,
                        c.symbol,
                        c.timeframe,
                        o.run_uuid,
                        o.runner_version,

                        COUNT(t.trade_no) AS trades,

                        SUM(t.gross_pnl) AS gross_pnl,
                        SUM(t.commission) AS commission,
                        SUM(t.slippage) AS slippage,
                        SUM(t.net_pnl) AS net_pnl,

                        AVG(t.net_pnl) AS net_expectancy,

                        SUM(
                            CASE
                                WHEN t.net_pnl > 0
                                THEN t.net_pnl
                                ELSE 0
                            END
                        ) AS gross_profit,

                        ABS(
                            SUM(
                                CASE
                                    WHEN t.net_pnl < 0
                                    THEN t.net_pnl
                                    ELSE 0
                                END
                            )
                        ) AS gross_loss,

                        MAX(x.verdict_code) AS oos_verdict

                    FROM analytics.edge_candidate_v1 c

                    JOIN analytics.edge_observation_v1 o
                      ON o.observation_uuid =
                         c.observation_uuid

                    JOIN analytics.research_trade_v1 t
                      ON t.run_uuid=o.run_uuid

                    LEFT JOIN analytics.edge_oos_result_v1 x
                      ON x.observation_uuid =
                         c.observation_uuid

                    WHERE
                        o.runner_version =
                        'STRATEGY_EXECUTION_RUNNER_V1'

                    GROUP BY
                        c.observation_uuid,
                        c.strategy_code,
                        c.symbol,
                        c.timeframe,
                        o.run_uuid,
                        o.runner_version
                )
                SELECT
                    *,
                    CASE
                        WHEN gross_loss > 0
                        THEN gross_profit / gross_loss
                        WHEN gross_profit > 0
                        THEN NULL
                        ELSE 0
                    END AS net_profit_factor
                FROM agg
                ORDER BY
                    strategy_code,
                    symbol,
                    observation_uuid
                """
            )

            rows = cur.fetchall()

    for row in rows:
        if row["net_profit_factor"] is None:
            raise RuntimeError(
                "ERROR=INFINITE_NET_PF_UNSUPPORTED "
                f"observation_uuid={row['observation_uuid']}"
            )

        result = evaluate_verified_net_admission_v1(
            metrics=VerifiedNetMetricsV1(
                trades=int(row["trades"]),
                net_profit_factor=D(
                    str(row["net_profit_factor"])
                ),
                net_expectancy=D(
                    str(row["net_expectancy"])
                ),
            ),
            policy=POLICY,
        )

        decision = (
            "WOULD_ADMIT"
            if result.passed
            else "WOULD_REJECT"
        )

        candidates += 1
        would_admit += int(result.passed)
        would_reject += int(not result.passed)

        print(
            "TRADE_LEVEL_SHADOW_ROW "
            f"observation_uuid={row['observation_uuid']} "
            f"strategy={row['strategy_code']} "
            f"symbol={row['symbol']} "
            f"timeframe={row['timeframe']} "
            f"trades={row['trades']} "
            f"gross_pnl={row['gross_pnl']} "
            f"commission={row['commission']} "
            f"slippage={row['slippage']} "
            f"net_pnl={row['net_pnl']} "
            f"net_expectancy={row['net_expectancy']} "
            f"net_profit_factor="
            f"{row['net_profit_factor']} "
            f"decision={decision} "
            f"economic_status={result.status} "
            f"oos_verdict={row['oos_verdict']}"
        )

    print(f"trade_level_candidates={candidates}")
    print(f"would_admit={would_admit}")
    print(f"would_reject={would_reject}")

    print("individual_trade_rows_used=1")
    print("persisted_trade_cost_evidence_used=1")
    print("aggregate_observation_costs_used=0")
    print("strategy_reconstruction_required=0")

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
        "TRADE_LEVEL_REAL_SHADOW_ADMISSION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
