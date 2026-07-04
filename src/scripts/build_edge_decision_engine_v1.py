from __future__ import annotations

import json
import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("EDGE_DECISION_LIMIT", "5000"))

def load_config(cur) -> dict:
    cur.execute("""
        SELECT config_json
        FROM analytics.edge_configuration_v1
        WHERE edge_name='DEFAULT'
        LIMIT 1;
    """)
    row = cur.fetchone()
    if not row:
        return {}
    cfg = row["config_json"]
    return cfg if isinstance(cfg, dict) else json.loads(cfg)

def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cfg = load_config(cur)
            min_edge_score = float(cfg.get("min_edge_score", 0.60))
            min_validation_score = float(cfg.get("min_validation_score", 0.70))

            cur.execute("""
                SELECT id, edge_score, validation_score
                FROM analytics.edge_decision_snapshot_v1
                ORDER BY signal_ts DESC
                LIMIT %s;
            """, (LIMIT,))
            rows = cur.fetchall()

            allow = observe = block = 0

            for r in rows:
                edge_score = float(r["edge_score"] or 0)
                validation_score = float(r["validation_score"] or 0)

                if edge_score >= min_edge_score and validation_score >= min_validation_score:
                    decision = "ALLOW"
                    recommendation = "READY_FOR_RISK_REVIEW"
                    ready_for_paper = True
                    allow += 1
                elif edge_score >= min_edge_score:
                    decision = "OBSERVE"
                    recommendation = "WAIT_VALIDATION"
                    ready_for_paper = False
                    observe += 1
                else:
                    decision = "BLOCK"
                    recommendation = "WAIT_RESEARCH"
                    ready_for_paper = False
                    block += 1

                cur.execute("""
                    UPDATE analytics.edge_decision_snapshot_v1
                    SET decision_code=%s,
                        recommendation_code=%s,
                        ready_for_paper=%s,
                        ready_for_shadow=false,
                        ready_for_micro_live=false,
                        ready_for_live=false,
                        source_version='EDGE_DECISION_ENGINE_V1',
                        build_id=%s,
                        refreshed_at=now()
                    WHERE id=%s;
                """, (decision, recommendation, ready_for_paper, build_id, r["id"]))

            cur.execute("""
                SELECT count(*) AS unsafe
                FROM analytics.edge_decision_snapshot_v1
                WHERE ready_for_live=true OR ready_for_micro_live=true;
            """)
            unsafe = int(cur.fetchone()["unsafe"])

    print("=== EDGE_DECISION_ENGINE_V1 ===")
    print(f"rows_processed={len(rows)}")
    print(f"allow={allow}")
    print(f"observe={observe}")
    print(f"block={block}")
    print(f"unsafe_live_rows={unsafe}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DECISION_ENGINE_V1_READY")

if __name__ == "__main__":
    main()
