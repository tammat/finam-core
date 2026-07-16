from __future__ import annotations

import uuid

import psycopg2
import psycopg2.extras


SOURCE_VERSION = "PROFIT_FUNNEL_OOS_FORWARD_HANDOFF_V2"
NAMESPACE = uuid.UUID("68c36ab7-49cc-50f5-a312-3d4fd32b0064")


def main() -> None:
    created = 0
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT c.candidate_uuid,c.observation_uuid,c.discovery_batch_id,c.research_batch_id,o.id oos_result_id
                FROM analytics.edge_candidate_v1 c
                JOIN analytics.edge_oos_result_v1 o ON o.observation_uuid=c.observation_uuid
                WHERE o.verdict_code='OOS_PASS' AND o.promotion_allowed=true
                ORDER BY c.candidate_uuid
            """)
            for row in cursor.fetchall():
                handoff_id = uuid.uuid5(NAMESPACE, f"handoff:{row['candidate_uuid']}")
                forward_candidate_id = uuid.uuid5(NAMESPACE, f"forward:{row['candidate_uuid']}")
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_oos_forward_handoff_v2 (
                        handoff_id,candidate_uuid,observation_uuid,discovery_batch_id,research_batch_id,
                        oos_result_id,forward_candidate_id,handoff_status,reason_code,
                        runtime_allowed,live_allowed,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDING','AWAITING_FORWARD_ADMISSION',false,false,%s)
                    ON CONFLICT (candidate_uuid) DO UPDATE SET
                        observation_uuid=EXCLUDED.observation_uuid,
                        discovery_batch_id=EXCLUDED.discovery_batch_id,
                        research_batch_id=EXCLUDED.research_batch_id,
                        oos_result_id=EXCLUDED.oos_result_id,
                        source_version=EXCLUDED.source_version,
                        updated_at=clock_timestamp()
                    WHERE analytics.profit_funnel_oos_forward_handoff_v2.handoff_status='PENDING'
                """, (
                    str(handoff_id),str(row["candidate_uuid"]),str(row["observation_uuid"]),
                    row["discovery_batch_id"],row["research_batch_id"],row["oos_result_id"],
                    str(forward_candidate_id),SOURCE_VERSION,
                ))
                created += int(cursor.rowcount > 0)
    print(f"eligible_oos_handoffs={created}")
    print("forward_incubator_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_PROFIT_FUNNEL_OOS_FORWARD_HANDOFF_V2_READY")


if __name__ == "__main__":
    main()
