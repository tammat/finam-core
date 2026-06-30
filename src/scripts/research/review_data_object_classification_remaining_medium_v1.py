#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

REFINED = {
    ("public", "cross_contract_liquidity_decisions"): ("GOVERNANCE", "APPLY", "liquidity_decision_governance"),
    ("research", "oos_validation_decisions_v1"): ("GOVERNANCE", "APPLY", "oos_validation_decision_governance"),
    ("public", "runtime_regime_overrides"): ("CONFIGURATION", "APPLY", "runtime_override_configuration"),
    ("public", "runtime_universe_rotation_log"): ("TELEMETRY", "APPLY", "runtime_rotation_log_telemetry"),
    ("public", "trusted_runtime_active_universe_sync_v1"): ("WORKFLOW", "APPLY", "runtime_sync_workflow"),
    ("research", "runtime_calibration_decisions_v1"): ("RESEARCH", "APPLY", "runtime_calibration_research"),
    ("public", "shadow_runtime_admission_board"): ("GOVERNANCE", "APPLY", "shadow_runtime_admission_governance"),
    ("research", "shadow_runtime_queue_v1"): ("WORKFLOW", "APPLY", "shadow_runtime_queue_workflow"),
    ("research", "shadow_runtime_runs_v1"): ("WORKFLOW", "APPLY", "shadow_runtime_runs_workflow"),
    ("public", "futures_mtf_regime"): ("CONFIGURATION", "APPLY", "regime_matrix_configuration"),
    ("public", "institutional_flow_regime_events"): ("ANALYTICS", "APPLY", "institutional_flow_analytics"),
    ("public", "ng_m1_session_regime_matrix"): ("CONFIGURATION", "APPLY", "regime_matrix_configuration"),
    ("public", "ng_session_regime_matrix"): ("CONFIGURATION", "APPLY", "regime_matrix_configuration"),
}

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.data_object_classification_remaining_medium_review_v1 (
    id bigserial PRIMARY KEY,
    schema_name text NOT NULL,
    table_name text NOT NULL,
    current_object_type text NOT NULL,
    previous_suggested_object_type text NOT NULL,
    refined_object_type text NOT NULL,
    decision text NOT NULL,
    refined_rule_name text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(schema_name, table_name)
);
"""

UPSERT = """
INSERT INTO warehouse.data_object_classification_remaining_medium_review_v1 (
    schema_name,
    table_name,
    current_object_type,
    previous_suggested_object_type,
    refined_object_type,
    decision,
    refined_rule_name
)
VALUES (%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (schema_name, table_name)
DO UPDATE SET
    current_object_type=EXCLUDED.current_object_type,
    previous_suggested_object_type=EXCLUDED.previous_suggested_object_type,
    refined_object_type=EXCLUDED.refined_object_type,
    decision=EXCLUDED.decision,
    refined_rule_name=EXCLUDED.refined_rule_name,
    active=true,
    updated_at=now();
"""

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_REVIEW_REMAINING_MEDIUM_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            cur.execute("""
                SELECT
                    schema_name,
                    table_name,
                    current_object_type,
                    suggested_object_type,
                    rule_name
                FROM warehouse.data_object_classification_review_v1
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='MEDIUM'
                ORDER BY schema_name, table_name;
            """)
            rows = cur.fetchall()

            apply_rows = 0
            skip_rows = 0
            changed_from_previous = 0

            for schema, table, current_type, previous_suggested, old_rule in rows:
                key = (schema, table)
                refined_type, decision, refined_rule = REFINED.get(
                    key,
                    ("OTHER", "SKIP", "no_refined_rule"),
                )

                if decision == "APPLY":
                    apply_rows += 1
                else:
                    skip_rows += 1

                if refined_type != previous_suggested:
                    changed_from_previous += 1

                cur.execute(
                    UPSERT,
                    (
                        schema,
                        table,
                        current_type,
                        previous_suggested,
                        refined_type,
                        decision,
                        refined_rule,
                    ),
                )

                print(
                    "REMAINING_MEDIUM"
                    f"|schema={schema}"
                    f"|table={table}"
                    f"|current={current_type}"
                    f"|previous_suggested={previous_suggested}"
                    f"|refined={refined_type}"
                    f"|decision={decision}"
                    f"|old_rule={old_rule}"
                    f"|refined_rule={refined_rule}"
                )

        conn.commit()

        print(f"remaining_medium_rows={len(rows)}")
        print(f"apply_rows={apply_rows}")
        print(f"skip_rows={skip_rows}")
        print(f"changed_from_previous_suggestion={changed_from_previous}")
        print("classification_changed=0")
        print("review_status_changed=0")
        print("database_write_mode=REVIEW_TABLE_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if len(rows) == 13 and apply_rows == 13 and skip_rows == 0:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_REVIEW_REMAINING_MEDIUM_V1_READY")
        else:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_REVIEW_REMAINING_MEDIUM_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
