from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

SOURCE_VERSION = "SIGNAL_FUNNEL_REASON_ANALYTICS_V1"

TARGET_TABLES = [
    ("public", "runtime_guard_signal_registry_v1"),
    ("public", "runtime_guard_pre_signal_block_audit_v1"),
    ("public", "runtime_candidate_decision_board"),
    ("public", "runtime_candidate_lifecycle_board"),
    ("public", "runtime_governance_decisions"),
    ("public", "runtime_allocator_decisions"),
    ("public", "risk_events"),
    ("public", "risk_event_audit_v1"),
    ("public", "order_reconciliation_issues"),
    ("public", "execution_events"),
    ("public", "execution_intents"),
    ("public", "signal_lifecycle"),
    ("public", "trade_context_snapshots"),
    ("analytics", "paper_execution_feedback_v1"),
    ("analytics", "recommendation_feedback_v1"),
    ("analytics", "risk_decision_snapshot_v1"),
    ("analytics", "trading_order_intent_v1"),
    ("knowledge", "recommendation_v1"),
    ("knowledge", "recommendation_reason_v1"),
    ("knowledge", "recommendation_execution_context_v1"),
]

REASON_COLUMN_PATTERNS = (
    "reason",
    "status",
    "decision",
    "reject",
    "block",
    "gate",
    "verdict",
)


def reason_group(value: str) -> str:
    v = value.upper()
    if "RISK" in v or "LIMIT" in v or "EXPOSURE" in v:
        return "RISK"
    if "EDGE" in v or "EXPECTANCY" in v or "PROFIT" in v:
        return "EDGE"
    if "REGIME" in v or "MARKET" in v or "SESSION" in v:
        return "MARKET"
    if "SAMPLE" in v or "DATA" in v or "MISSING" in v:
        return "DATA"
    if "ORDER" in v or "FILL" in v or "EXECUTION" in v or "BROKER" in v:
        return "EXECUTION"
    if "LOCK" in v or "BLOCK" in v or "REJECT" in v:
        return "BLOCK"
    if "ALLOW" in v or "PASS" in v or "READY" in v:
        return "PASS"
    return "OTHER"


def table_exists(cur, schema_name: str, table_name: str) -> bool:
    cur.execute(
        """
        SELECT count(*) AS rows_total
        FROM information_schema.tables
        WHERE table_schema=%s
          AND table_name=%s
        """,
        (schema_name, table_name),
    )
    return int(cur.fetchone()["rows_total"]) == 1


def reason_columns(cur, schema_name: str, table_name: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema=%s
          AND table_name=%s
          AND data_type IN ('text','character varying','character')
        ORDER BY ordinal_position
        """,
        (schema_name, table_name),
    )
    cols = [str(r["column_name"]) for r in cur.fetchall()]
    return [
        c for c in cols
        if any(p in c.lower() for p in REASON_COLUMN_PATTERNS)
    ]


def collect_column_values(cur, schema_name: str, table_name: str, column_name: str) -> list[dict[str, Any]]:
    cur.execute(
        sql.SQL("""
            SELECT
                {col}::text AS reason_value,
                count(*)::numeric AS rows_total
            FROM {schema}.{table}
            WHERE {col} IS NOT NULL
              AND length(trim({col}::text)) > 0
            GROUP BY {col}::text
            ORDER BY rows_total DESC, reason_value
            LIMIT 100
        """).format(
            col=sql.Identifier(column_name),
            schema=sql.Identifier(schema_name),
            table=sql.Identifier(table_name),
        )
    )
    return [dict(r) for r in cur.fetchall()]


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.signal_funnel_reason_snapshot_v1
                (source_version, evidence_json)
                VALUES (%s,%s::jsonb)
                RETURNING signal_funnel_reason_snapshot_id
            """, (
                SOURCE_VERSION,
                json.dumps({"mode": "read_only_reason_analytics"}, ensure_ascii=False),
            ))
            snapshot_id = int(cur.fetchone()["signal_funnel_reason_snapshot_id"])

            inserted = 0
            scanned_tables = 0
            scanned_columns = 0

            for schema_name, table_name in TARGET_TABLES:
                if not table_exists(cur, schema_name, table_name):
                    continue

                scanned_tables += 1
                cols = reason_columns(cur, schema_name, table_name)

                for col in cols:
                    scanned_columns += 1
                    rows = collect_column_values(cur, schema_name, table_name, col)

                    for row in rows:
                        value = str(row["reason_value"])
                        count = Decimal(str(row["rows_total"] or 0))

                        cur.execute("""
                            INSERT INTO analytics.signal_funnel_reason_v1
                            (
                                signal_funnel_reason_snapshot_id,
                                source_schema,
                                source_table,
                                reason_column,
                                reason_value,
                                rows_total,
                                reason_group,
                                evidence_json,
                                source_version
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                        """, (
                            snapshot_id,
                            schema_name,
                            table_name,
                            col,
                            value,
                            count,
                            reason_group(value),
                            json.dumps(
                                {
                                    "source": f"{schema_name}.{table_name}.{col}",
                                    "method": "distinct_value_count",
                                },
                                ensure_ascii=False,
                            ),
                            SOURCE_VERSION,
                        ))
                        inserted += 1

    print("=== SIGNAL_FUNNEL_REASON_ANALYTICS_V1 ===")
    print(f"signal_funnel_reason_snapshot_id={snapshot_id}")
    print(f"scanned_tables={scanned_tables}")
    print(f"scanned_columns={scanned_columns}")
    print(f"reason_rows_inserted={inserted}")
    print("mode=read_only_reason_analytics")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=SIGNAL_FUNNEL_REASON_ANALYTICS_V1_READY")


if __name__ == "__main__":
    main()
