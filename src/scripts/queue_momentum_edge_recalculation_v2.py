from __future__ import annotations

import os
from datetime import UTC, datetime

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BATCH_ID = os.getenv(
    "RESEARCH_BATCH_ID",
    datetime.now(UTC).strftime("%Y%m%d_MOMENTUM_THRESHOLD_RECALC_V2"),
)
CANDIDATE_IDS = tuple(
    int(value) for value in os.getenv("EDGE_CANDIDATE_IDS", "20,21,22,23,24").split(",")
)


def main() -> None:
    queued = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM analytics.edge_candidate_v1
                WHERE id = ANY(%s)
                  AND strategy_code='MOMENTUM_CONTINUATION_V1'
                ORDER BY id;
                """,
                (list(CANDIDATE_IDS),),
            )
            candidates = cur.fetchall()
            if len(candidates) != len(CANDIDATE_IDS):
                raise RuntimeError(
                    f"CANDIDATE_SET_INCOMPLETE expected={len(CANDIDATE_IDS)} actual={len(candidates)}"
                )

            for candidate in candidates:
                research_code = f"{candidate['research_code']}:RECALC_V2:C{candidate['id']}"
                cur.execute(
                    """
                    INSERT INTO analytics.edge_lab_run_v1 (
                        research_batch_id,research_code,strategy_code,strategy_version,
                        symbol,timeframe,parameter_hash,parameter_json,dataset_version,
                        runner_version,status_code,source_version,updated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'QUEUED',%s,now())
                    ON CONFLICT (
                        research_code,strategy_code,symbol,timeframe,parameter_hash,dataset_version
                    ) DO NOTHING
                    RETURNING id;
                    """,
                    (
                        BATCH_ID,
                        research_code,
                        candidate["strategy_code"],
                        candidate["strategy_version"],
                        candidate["symbol"],
                        candidate["timeframe"],
                        candidate["parameter_hash"],
                        psycopg2.extras.Json(candidate["parameter_json"] or {}),
                        candidate["dataset_version"],
                        "STRATEGY_EXECUTION_RUNNER_V2",
                        "MOMENTUM_THRESHOLD_RECALC_V2",
                    ),
                )
                queued += int(cur.fetchone() is not None)

    print(f"research_batch_id={BATCH_ID}")
    print(f"candidate_ids={','.join(str(value) for value in CANDIDATE_IDS)}")
    print(f"queued={queued}")
    print("historical_observations_changed=0")
    print("runtime_changed=0")
    print("orders_changed=0")
    print("VERDICT=QUEUE_MOMENTUM_EDGE_RECALCULATION_V2_OK")


if __name__ == "__main__":
    main()
