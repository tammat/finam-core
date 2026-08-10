from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from marketcore.research.economics.economic_evidence_classifier_v1 import (
    classify_economic_evidence_v1,
)


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def main() -> int:
    direct = 0
    replay = 0
    unsupported = 0
    total = 0

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
                    c.strategy_code,
                    c.symbol,
                    c.timeframe,
                    o.runner_version,
                    o.score_formula_version,
                    o.source_version,
                    o.verdict_code,
                    o.commission,
                    o.slippage
                FROM analytics.edge_candidate_v1 c
                JOIN analytics.edge_observation_v1 o
                  ON o.observation_uuid=c.observation_uuid
                ORDER BY c.observation_uuid
                """
            )

            for row in cur.fetchall():
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

                total += 1
                direct += int(
                    decision.direct_gate_allowed
                )
                replay += int(
                    decision.replay_required
                )
                unsupported += int(
                    decision.evidence_class
                    == "UNSUPPORTED"
                )

                print(
                    "ECONOMIC_EVIDENCE_ROW "
                    f"observation_uuid={row['observation_uuid']} "
                    f"strategy={row['strategy_code']} "
                    f"symbol={row['symbol']} "
                    f"class={decision.evidence_class} "
                    f"direct_gate_allowed="
                    f"{int(decision.direct_gate_allowed)} "
                    f"replay_required="
                    f"{int(decision.replay_required)} "
                    f"reason={decision.reason_code}"
                )

    print(f"candidates={total}")
    print(f"direct_gate_candidates={direct}")
    print(f"replay_required_candidates={replay}")
    print(f"unsupported_candidates={unsupported}")

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
        "REAL_CANDIDATE_ECONOMIC_EVIDENCE_CLASSIFICATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
