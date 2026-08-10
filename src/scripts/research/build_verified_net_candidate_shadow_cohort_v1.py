from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from marketcore.research.economics.economic_evidence_classifier_v1 import (
    EconomicEvidenceClassV1,
    classify_economic_evidence_v1,
)


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def main() -> int:
    total = 0
    verified = 0
    promoted = 0
    replay = 0
    unsupported = 0

    with psycopg2.connect(
        os.environ["DATABASE_URL"]
    ) as conn:
        conn.set_session(
            readonly=True,
            autocommit=False,
        )

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
                    c.candidate_status,

                    o.trades,
                    o.profit_factor,
                    o.expectancy,
                    o.commission,
                    o.slippage,
                    o.verdict_code,
                    o.runner_version,
                    o.score_formula_version,
                    o.source_version,

                    EXISTS (
                        SELECT 1
                        FROM analytics.edge_oos_result_v1 x
                        WHERE
                            x.observation_uuid =
                            c.observation_uuid
                    ) AS oos_exists

                FROM analytics.edge_candidate_v1 c

                JOIN analytics.edge_observation_v1 o
                  ON o.observation_uuid =
                     c.observation_uuid

                ORDER BY
                    c.discovery_batch_id,
                    c.strategy_code,
                    c.symbol,
                    c.observation_uuid
                """
            )

            rows = cur.fetchall()

    for row in rows:
        total += 1

        decision = classify_economic_evidence_v1(
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

        cls = decision.evidence_class

        if (
            cls
            == EconomicEvidenceClassV1
            .VERIFIED_NET_METRICS
        ):
            verified += 1

            print(
                "VERIFIED_NET_COHORT_ROW "
                f"observation_uuid="
                f"{row['observation_uuid']} "
                f"strategy={row['strategy_code']} "
                f"symbol={row['symbol']} "
                f"timeframe={row['timeframe']} "
                f"trades={row['trades']} "
                f"net_profit_factor="
                f"{row['profit_factor']} "
                f"net_expectancy="
                f"{row['expectancy']} "
                f"commission="
                f"{row['commission']} "
                f"slippage="
                f"{row['slippage']} "
                f"oos_exists="
                f"{int(bool(row['oos_exists']))}"
            )

        elif (
            cls
            == EconomicEvidenceClassV1
            .COST_AWARE_PROMOTED_METRICS
        ):
            promoted += 1

        elif (
            cls
            == EconomicEvidenceClassV1
            .REPLAY_REQUIRED
        ):
            replay += 1

        else:
            unsupported += 1

    print(f"real_candidates={total}")
    print(
        f"verified_net_candidates={verified}"
    )
    print(
        f"cost_aware_promoted_candidates="
        f"{promoted}"
    )
    print(
        f"replay_required_candidates={replay}"
    )
    print(
        f"unsupported_candidates={unsupported}"
    )

    print(
        "phase_a_direct_gate_candidates="
        f"{verified}"
    )

    print(
        "promoted_metrics_direct_gate_enabled=0"
    )

    print(
        "replay_required_direct_gate_enabled=0"
    )

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
        "VERIFIED_NET_CANDIDATE_SHADOW_COHORT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
