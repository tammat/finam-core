from __future__ import annotations

import uuid

import psycopg2

SOURCE_VERSION = "PROFIT_FUNNEL_RUNTIME_LIVE_ADMISSION_V2"
NAMESPACE = uuid.UUID("29757126-ddcf-566c-a652-931f3bd48129")


def main() -> None:
    created = 0
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT admission_id,runtime_candidate_id
                FROM analytics.profit_funnel_paper_runtime_admission_v2
                WHERE admission_status='ADMITTED' AND runtime_allowed
                ORDER BY admission_id
            """)
            rows = cursor.fetchall()
            for runtime_admission_id, runtime_candidate_id in rows:
                admission_id = uuid.uuid5(NAMESPACE, "admission:" + str(runtime_candidate_id))
                live_candidate_id = uuid.uuid5(NAMESPACE, "live:" + str(runtime_candidate_id))
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_runtime_live_admission_v2 (
                        admission_id,runtime_admission_id,runtime_candidate_id,live_candidate_id,
                        admission_status,reason_code,broker_order_allowed,execution_enabled,
                        live_allowed,source_version
                    ) VALUES (%s,%s,%s,%s,'PENDING','AWAITING_LIVE_RISK_AUTHORIZATION',false,false,false,%s)
                    ON CONFLICT (runtime_admission_id) DO UPDATE SET updated_at=clock_timestamp()
                    WHERE analytics.profit_funnel_runtime_live_admission_v2.admission_status='PENDING'
                """, (str(admission_id),str(runtime_admission_id),str(runtime_candidate_id),
                      str(live_candidate_id),SOURCE_VERSION))
                created += int(cursor.rowcount > 0)
    print(f"runtime_candidates_admitted={len(rows)}")
    print(f"live_admissions_pending={created}")
    print("broker_order_allowed=0")
    print("execution_changed=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_RUNTIME_LIVE_ADMISSION_V2_READY")


if __name__ == "__main__":
    main()
