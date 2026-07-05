from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BATCH_ID = os.getenv("RESEARCH_BATCH_ID", datetime.utcnow().strftime("%Y%m%d_EDGE_LAB_BOOTSTRAP"))


def parameter_hash(parameter_set: object) -> str:
    raw = json.dumps(parameter_set or {}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def main() -> None:
    created = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    research_code,
                    strategy_code,
                    symbol,
                    timeframe,
                    parameter_set
                FROM analytics.research_queue_v1
                WHERE status_code='QUEUED'
                ORDER BY priority ASC, id ASC;
            """)
            rows = cur.fetchall()

            for r in rows:
                params = r["parameter_set"] or {}
                ph = parameter_hash(params)

                cur.execute("""
                    INSERT INTO analytics.edge_lab_run_v1 (
                        research_batch_id,
                        research_code,
                        strategy_code,
                        strategy_version,
                        symbol,
                        timeframe,
                        parameter_hash,
                        parameter_json,
                        dataset_version,
                        runner_version,
                        status_code,
                        source_version,
                        updated_at
                    )
                    VALUES (
                        %s,%s,%s,'v1',%s,%s,%s,%s::jsonb,
                        'default',
                        'EDGE_LAB_FOUNDATION_V1',
                        'QUEUED',
                        'EDGE_LAB_FOUNDATION_V1',
                        now()
                    )
                    ON CONFLICT(research_code, strategy_code, symbol, timeframe, parameter_hash, dataset_version)
                    DO UPDATE SET
                        research_batch_id=EXCLUDED.research_batch_id,
                        parameter_json=EXCLUDED.parameter_json,
                        runner_version=EXCLUDED.runner_version,
                        status_code='QUEUED',
                        source_version='EDGE_LAB_FOUNDATION_V1',
                        updated_at=now();
                """, (
                    BATCH_ID,
                    r["research_code"],
                    r["strategy_code"],
                    r["symbol"],
                    r["timeframe"],
                    ph,
                    json.dumps(params, ensure_ascii=False, sort_keys=True),
                ))
                created += 1

            cur.execute("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE status_code='QUEUED') AS queued,
                    count(*) FILTER (WHERE status_code='RUNNING') AS running,
                    count(*) FILTER (WHERE status_code='DONE') AS done,
                    count(*) FILTER (WHERE status_code='FAILED') AS failed
                FROM analytics.edge_lab_run_v1;
            """)
            summary = cur.fetchone()

    print("=== EDGE_LAB_FOUNDATION_V1 ===")
    print(f"research_batch_id={BATCH_ID}")
    print(f"runs_generated={created}")
    print(f"runs_total={summary['total']}")
    print(f"queued={summary['queued']}")
    print(f"running={summary['running']}")
    print(f"done={summary['done']}")
    print(f"failed={summary['failed']}")
    print("observations_created=0")
    print("candidates_created=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_LAB_FOUNDATION_V1_READY")


if __name__ == "__main__":
    main()
