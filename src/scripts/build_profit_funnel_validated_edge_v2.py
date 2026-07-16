from __future__ import annotations

import uuid

import psycopg2

SOURCE_VERSION = "PROFIT_FUNNEL_VALIDATED_EDGE_V2"
NAMESPACE = uuid.UUID("01ace818-b308-56f4-a392-36f66d207dcc")


def main() -> None:
    inserted = 0
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT candidate_uuid,observation_uuid,discovery_batch_id,validation_score,
                       validation_formula_version,updated_at
                FROM analytics.edge_candidate_v1
                WHERE validation_score IS NOT NULL AND validation_formula_version IS NOT NULL
                ORDER BY candidate_uuid
            """)
            rows = cursor.fetchall()
            for candidate_uuid, observation_uuid, batch_id, score, formula, validated_at in rows:
                validation_id = uuid.uuid5(NAMESPACE, "validation:" + str(candidate_uuid))
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_validated_edge_v2 (
                        validation_id,candidate_uuid,observation_uuid,discovery_batch_id,
                        validation_score,validation_formula_version,validation_status,
                        paper_allowed,runtime_allowed,live_allowed,source_version,validated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,'PASS',false,false,false,%s,%s)
                    ON CONFLICT (candidate_uuid) DO NOTHING
                """, (str(validation_id),str(candidate_uuid),str(observation_uuid),batch_id,
                      score,formula,SOURCE_VERSION,validated_at))
                inserted += cursor.rowcount
    print(f"eligible_validated_edges={len(rows)}")
    print(f"inserted_validated_edges={inserted}")
    print("paper_changed=0")
    print("runtime_changed=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_PROFIT_FUNNEL_VALIDATED_EDGE_V2_READY")


if __name__ == "__main__":
    main()
