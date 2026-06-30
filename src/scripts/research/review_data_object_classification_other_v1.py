#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.data_object_classification_review_v1 (
    id bigserial PRIMARY KEY,
    schema_name text NOT NULL,
    table_name text NOT NULL,
    current_object_type text NOT NULL,
    suggested_object_type text NOT NULL,
    confidence text NOT NULL,
    rule_name text NOT NULL,
    review_status text NOT NULL DEFAULT 'SUGGESTED',
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(schema_name, table_name)
);
"""

UPSERT = """
INSERT INTO warehouse.data_object_classification_review_v1 (
    schema_name,
    table_name,
    current_object_type,
    suggested_object_type,
    confidence,
    rule_name
)
VALUES (%s,%s,%s,%s,%s,%s)
ON CONFLICT (schema_name, table_name)
DO UPDATE SET
    current_object_type=EXCLUDED.current_object_type,
    suggested_object_type=EXCLUDED.suggested_object_type,
    confidence=EXCLUDED.confidence,
    rule_name=EXCLUDED.rule_name,
    review_status='SUGGESTED',
    active=true,
    updated_at=now();
"""

def suggest(schema: str, table: str) -> tuple[str, str, str]:
    name = f"{schema}.{table}".lower()

    if table.endswith("_journal"):
        return "AUDIT", "HIGH", "suffix_journal"
    if table.endswith("_calendar"):
        return "REFERENCE", "HIGH", "suffix_calendar"
    if table.endswith("_universe"):
        return "REFERENCE", "HIGH", "suffix_universe"
    if table.endswith("_reference"):
        return "REFERENCE", "HIGH", "suffix_reference"
    if "watchlist" in table:
        return "REFERENCE", "HIGH", "contains_watchlist"
    if "observation" in table or "observations" in table:
        return "TELEMETRY", "HIGH", "contains_observation"
    if "scan_results" in table:
        return "ANALYTICS", "HIGH", "suffix_scan_results"
    if table.startswith("trade_attribution"):
        return "ANALYTICS", "HIGH", "prefix_trade_attribution"
    if table.startswith("trade_outcomes"):
        return "ANALYTICS", "HIGH", "prefix_trade_outcomes"
    if "context_envelope" in table:
        return "RUNTIME_STATE", "HIGH", "contains_context_envelope"
    if "dead_letter" in table or table == "event_store" or table == "events":
        return "WORKFLOW", "MEDIUM", "event_infra"
    if "allocator" in table:
        return "GOVERNANCE", "HIGH", "contains_allocator"
    if "review" in table or "package" in table or "readiness" in table:
        return "GOVERNANCE", "HIGH", "review_package_readiness"
    if "mark_to_market" in table or "mtm" in table:
        return "PORTFOLIO", "HIGH", "mark_to_market"
    if "shadow_runtime" in table:
        return "RUNTIME_STATE", "MEDIUM", "prefix_shadow_runtime"
    if "runtime" in table:
        return "RUNTIME_STATE", "MEDIUM", "prefix_runtime"
    if "session_regime_matrix" in table or "regime" in table:
        return "CONFIGURATION", "MEDIUM", "regime_matrix"
    if "liquidity" in table or "decisions" in table:
        return "GOVERNANCE", "MEDIUM", "decision_table"
    if "profit_lock" in table or "take_profit" in table or "trailing" in table:
        return "EXECUTION", "MEDIUM", "exit_event_state"
    if "market_event" in table:
        return "REFERENCE", "MEDIUM", "market_event"
    if "flow_regime" in table:
        return "ANALYTICS", "MEDIUM", "flow_regime"
    if "paper" in table:
        return "ANALYTICS", "MEDIUM", "paper_analysis"
    if "oos_validation" in table:
        return "RESEARCH", "HIGH", "oos_validation"
    if "calibration" in table:
        return "RESEARCH", "HIGH", "calibration"
    if "queue" in table or "runs" in table:
        return "WORKFLOW", "MEDIUM", "queue_or_runs"

    return "OTHER", "LOW", "no_rule_matched"

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_REVIEW_OTHER_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            cur.execute("""
                SELECT schema_name, table_name, object_type
                FROM warehouse.data_object_classification_v1
                WHERE active=true
                  AND object_type='OTHER'
                ORDER BY schema_name, table_name;
            """)
            rows = cur.fetchall()

            high = medium = low = changed = 0

            for schema, table, current_type in rows:
                suggested, confidence, rule = suggest(schema, table)
                if confidence == "HIGH":
                    high += 1
                elif confidence == "MEDIUM":
                    medium += 1
                else:
                    low += 1

                if suggested != current_type:
                    changed += 1

                cur.execute(UPSERT, (schema, table, current_type, suggested, confidence, rule))

                print(
                    "REVIEW"
                    f"|schema={schema}"
                    f"|table={table}"
                    f"|current={current_type}"
                    f"|suggested={suggested}"
                    f"|confidence={confidence}"
                    f"|rule={rule}"
                )

        conn.commit()

        print(f"review_rows={len(rows)}")
        print(f"suggested_changes={changed}")
        print(f"high_confidence={high}")
        print(f"medium_confidence={medium}")
        print(f"low_confidence={low}")
        print("review_status=SUGGESTED_ONLY")
        print("classification_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=DATA_OBJECT_CLASSIFICATION_REVIEW_OTHER_V1_READY")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
