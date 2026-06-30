#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

SAFE_RULES = {
    "event_infra",
    "exit_event_state",
    "paper_analysis",
    "queue_or_runs",
}

REVIEW_RULES = {
    "prefix_runtime",
    "prefix_shadow_runtime",
    "regime_matrix",
    "decision_table",
    "flow_regime",
    "market_event",
}

def decision_group(rule_name: str) -> str:
    if rule_name in SAFE_RULES:
        return "SAFE"
    if rule_name in REVIEW_RULES:
        return "REVIEW"
    return "SKIP"

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_CONFIDENCE_DRY_RUN_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    schema_name,
                    table_name,
                    current_object_type,
                    suggested_object_type,
                    confidence,
                    rule_name
                FROM warehouse.data_object_classification_review_v1
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='MEDIUM'
                ORDER BY rule_name, schema_name, table_name;
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT object_type, count(*)
                FROM warehouse.data_object_classification_v1
                WHERE active=true
                GROUP BY object_type
                ORDER BY object_type;
            """)
            current_counts = dict(cur.fetchall())

        rule_counts: dict[str, int] = defaultdict(int)
        group_counts: dict[str, int] = defaultdict(int)
        estimated_counts = dict(current_counts)

        for schema, table, current_type, suggested_type, confidence, rule_name in rows:
            group = decision_group(rule_name)
            rule_counts[rule_name] += 1
            group_counts[group] += 1

            if suggested_type != current_type:
                estimated_counts[current_type] = estimated_counts.get(current_type, 0) - 1
                estimated_counts[suggested_type] = estimated_counts.get(suggested_type, 0) + 1

        print("SECTION=SUMMARY")
        print(f"medium_rows={len(rows)}")
        print(f"safe_rows={group_counts.get('SAFE', 0)}")
        print(f"review_rows={group_counts.get('REVIEW', 0)}")
        print(f"skip_rows={group_counts.get('SKIP', 0)}")

        print("SECTION=RULES")
        for rule_name in sorted(rule_counts):
            print(
                f"RULE|rule={rule_name}"
                f"|count={rule_counts[rule_name]}"
                f"|group={decision_group(rule_name)}"
            )

        print("SECTION=OBJECTS")
        for schema, table, current_type, suggested_type, confidence, rule_name in rows:
            group = decision_group(rule_name)
            print(
                f"OBJECT|group={group}"
                f"|schema={schema}"
                f"|table={table}"
                f"|current={current_type}"
                f"|suggested={suggested_type}"
                f"|confidence={confidence}"
                f"|rule={rule_name}"
            )

        print("SECTION=ESTIMATED_OBJECT_TYPE_COUNTS")
        for object_type in sorted(estimated_counts):
            print(f"ESTIMATE|type={object_type}|tables={estimated_counts[object_type]}")

        print("SECTION=CHECKS")
        print("classification_changed=0")
        print("review_status_changed=0")
        print("database_write_mode=DRY_RUN_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if len(rows) == 20:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_CONFIDENCE_DRY_RUN_V1_READY")
        else:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_CONFIDENCE_DRY_RUN_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
