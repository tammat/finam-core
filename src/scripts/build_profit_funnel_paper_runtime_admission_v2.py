from __future__ import annotations

import uuid

import psycopg2

SOURCE_VERSION = "PROFIT_FUNNEL_PAPER_RUNTIME_ADMISSION_V2"
NAMESPACE = uuid.UUID("8bc31d1f-ff17-5062-a4ae-e22be85ba09c")


def main() -> None:
    blocked = pending = 0
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE analytics.paper_runtime_candidate_v1 p
                SET paper_status='BLOCKED_OOS_FAIL',updated_at=clock_timestamp()
                FROM analytics.edge_candidate_v1 c
                WHERE c.observation_uuid=p.observation_uuid
                  AND p.paper_status='ACTIVE'
                  AND (c.candidate_status='OOS_FAIL' OR NOT c.paper_allowed)
            """)
            blocked = cursor.rowcount
            cursor.execute("""
                SELECT p.id,p.observation_uuid
                FROM analytics.paper_runtime_candidate_v1 p
                JOIN analytics.edge_candidate_v1 c USING (observation_uuid)
                WHERE p.paper_status='ACTIVE' AND c.candidate_status='OOS_PASS' AND c.paper_allowed
                ORDER BY p.id
            """)
            rows = cursor.fetchall()
            for paper_id, observation_uuid in rows:
                admission_id = uuid.uuid5(NAMESPACE, "admission:" + str(observation_uuid))
                runtime_id = uuid.uuid5(NAMESPACE, "runtime:" + str(observation_uuid))
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_paper_runtime_admission_v2 (
                        admission_id,paper_candidate_id,observation_uuid,runtime_candidate_id,
                        admission_status,reason_code,runtime_allowed,execution_enabled,live_allowed,source_version
                    ) VALUES (%s,%s,%s,%s,'PENDING','AWAITING_RUNTIME_ADMISSION',false,false,false,%s)
                    ON CONFLICT (paper_candidate_id) DO UPDATE SET updated_at=clock_timestamp()
                    WHERE analytics.profit_funnel_paper_runtime_admission_v2.admission_status='PENDING'
                """, (str(admission_id),paper_id,str(observation_uuid),str(runtime_id),SOURCE_VERSION))
                pending += int(cursor.rowcount > 0)
    print(f"paper_candidates_blocked_oos_fail={blocked}")
    print(f"paper_runtime_pending={pending}")
    print("runtime_allowed=0")
    print("execution_changed=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_PAPER_RUNTIME_ADMISSION_V2_READY")


if __name__ == "__main__":
    main()
