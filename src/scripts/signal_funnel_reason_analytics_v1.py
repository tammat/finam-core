from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

SOURCE_VERSION = "SIGNAL_FUNNEL_REASON_ANALYTICS_V6_CURRENT_SESSION"

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
    v = " ".join(value.upper().strip().split())
    if not v or v in {"UNKNOWN", "NONE", "NULL", "N/A", "NA"}:
        return "UNKNOWN"
    if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", v):
        return "UNKNOWN"
    if any(token in v for token in (
        "PYRAMID", "ANTI_REENTRY", "OPEN_POSITION", "ALREADY_OPEN",
        "CLUSTER_BLOCK", "TRADE_LIMIT", "DB_QUOTA", "KILL_SWITCH",
    )):
        return "PROTECTION"
    if "ACCEPTED_WITHOUT_ORDER" in v or "SUPERSEDED_AFTER_PIPELINE_RESTART" in v:
        return "CONTROL"
    if "TREND_FLIP" in v:
        return "MARKET"
    if "STRATEGY_BLOCKED" in v or "СТРАТЕГИЯ_ЗАБЛОКИРОВАНА_ПО_СТАТИСТИКЕ" in v:
        return "EDGE"
    if any(token in v for token in (
        "POLICY_UNAVAILABLE", "UNKNOWN_REGIME", "SIGNAL_LIFECYCLE_TIMEOUT",
        "NOT_PROCESSED",
    )):
        return "TECHNICAL"
    if "SHADOW_ONLY" in v or "NO_PROMOTED_OOS" in v:
        return "RESEARCH"
    if any(token in v for token in ("SAMPLE", "DATA", "MISSING", "HISTORY", "STALE", "FRESHNESS", "COVERAGE")):
        return "DATA"
    if any(token in v for token in ("VOLATILITY", "VOL_LOW", "LOW_VOL", "HIGH_VOL", "ATR_")):
        return "VOLATILITY"
    if any(token in v for token in ("LIQUID", "SPREAD", "SLIPPAGE")):
        return "LIQUIDITY"
    if "RISK" in v or "LIMIT" in v or "EXPOSURE" in v or "PYRAMID" in v:
        return "RISK"
    if "EDGE" in v or "EXPECTANCY" in v or "PROFIT" in v:
        return "EDGE"
    if "REGIME" in v or "MARKET" in v or "SESSION" in v:
        return "MARKET"
    if any(token in v for token in ("TIME_EXIT", "TIME_EXPIRED", "STOP_LOSS", "STALL_EXIT", "PROTECTIVE", "TAKE_PROFIT", "TRAILING_STOP")):
        return "EXIT"
    if any(token in v for token in ("COMPRESSION", "BREAKOUT", "RETEST", "MOMENTUM", "MEAN_REVERSION", "SIGNAL", "SETUP")):
        return "SETUP"
    if "ORDER" in v or "FILL" in v or "EXECUTION" in v or "BROKER" in v:
        return "EXECUTION"
    if any(token in v for token in ("RESEARCH", "WATCH", "SHADOW_VALIDATION", "REVIEW", "ИССЛЕДОВАН")):
        return "RESEARCH"
    if any(token in v for token in ("DRY_RUN", "ARCHIVED", "CHECKPOINT", "LIFECYCLE")):
        return "LIFECYCLE"
    if any(token in v for token in ("LOCK", "BLOCK", "REJECT", "ЗАБЛОКИРОВАН")):
        return "BLOCK"
    if any(token in v for token in ("ALLOW", "PASS", "READY", "ACCEPTED", "SELECTED", "PROMOTE", "РАЗРЕШЕН", "РАЗРЕШЁН")):
        return "PASS"
    if any(token in v for token in ("NO_EFFECT", "UNSTABLE", "NOISE", "DEGRADED")):
        return "QUALITY"
    if v in {"ACTIVE", "INACTIVE", "PENDING"}:
        return "LIFECYCLE"
    return "OTHER"


def collect_admission_losses(cur) -> list[dict[str, Any]]:
    """Считает только сигналы сопоставимой когорты, не дошедшие до заявки."""
    cur.execute("""
        WITH signal_rows AS (
            SELECT id,
                   COALESCE(NULLIF(signal_id,''),id::text) AS signal_key,
                   COALESCE(NULLIF(status,''),'UNKNOWN') AS signal_status,
                   NULLIF(trim(rejection_reason),'') AS rejection_reason,
                   symbol,
                   concat_ws('|',
                       COALESCE(NULLIF(symbol,''),'UNKNOWN'),
                       COALESCE(NULLIF(upper(side),''),'UNKNOWN'),
                       COALESCE(NULLIF(strategy,''),'UNKNOWN'),
                       COALESCE(NULLIF(upper(timeframe),''),'UNKNOWN'),
                       COALESCE(
                           NULLIF(payload #>> '{features,regime_bar_ts}',''),
                           NULLIF(payload #>> '{metadata,bar_ts}',''),
                           date_bin(
                               CASE upper(COALESCE(timeframe,'M5'))
                                   WHEN 'M1' THEN interval '1 minute'
                                   WHEN 'M15' THEN interval '15 minutes'
                                   WHEN 'H1' THEN interval '1 hour'
                                   ELSE interval '5 minutes'
                               END,
                               ts,
                               timestamptz '2000-01-01 00:00:00+00'
                           )::text
                       )
                   ) AS opportunity_key,
                   row_number() OVER (
                       PARTITION BY
                           COALESCE(NULLIF(symbol,''),'UNKNOWN'),
                           COALESCE(NULLIF(upper(side),''),'UNKNOWN'),
                           COALESCE(NULLIF(strategy,''),'UNKNOWN'),
                           COALESCE(NULLIF(upper(timeframe),''),'UNKNOWN'),
                           COALESCE(
                               NULLIF(payload #>> '{features,regime_bar_ts}',''),
                               NULLIF(payload #>> '{metadata,bar_ts}',''),
                               date_bin(
                                   CASE upper(COALESCE(timeframe,'M5'))
                                       WHEN 'M1' THEN interval '1 minute'
                                       WHEN 'M15' THEN interval '15 minutes'
                                       WHEN 'H1' THEN interval '1 hour'
                                       ELSE interval '5 minutes'
                                   END,
                                   ts,
                                   timestamptz '2000-01-01 00:00:00+00'
                               )::text
                           )
                       ORDER BY created_at DESC,id DESC
                   ) AS recency_rank
            FROM public.signals
            WHERE created_at >= (
                date_trunc('day',clock_timestamp() AT TIME ZONE 'Europe/Moscow')
                AT TIME ZONE 'Europe/Moscow'
            )
        ), signal_cohort AS (
            SELECT * FROM signal_rows WHERE recency_rank=1
        ), admission_losses AS (
            SELECT s.*,
                   COALESCE(s.rejection_reason,
                       CASE upper(s.signal_status)
                         WHEN 'ACCEPTED' THEN 'ACCEPTED_WITHOUT_ORDER'
                         WHEN 'RISK_ACCEPTED' THEN 'RISK_ACCEPTED_WITHOUT_ORDER'
                         WHEN 'NEW' THEN 'NEW_NOT_PROCESSED'
                         ELSE upper(s.signal_status)
                       END) AS reason_value
            FROM signal_cohort s
            WHERE NOT EXISTS (
                SELECT 1 FROM signal_rows member
                JOIN public.orders o ON o.signal_event_id=member.signal_key
                WHERE member.opportunity_key=s.opportunity_key
            )
              AND NOT EXISTS (
                SELECT 1 FROM signal_rows member
                JOIN public.signal_fills sf ON sf.signal_id=member.signal_key
                WHERE member.opportunity_key=s.opportunity_key
            )
        )
        SELECT reason_value,count(*)::numeric AS rows_total,
               jsonb_build_object(
                   'cohort','unique_closed_bar_opportunity_v5_paper_aware',
                   'boundary','RESEARCH_TO_EXECUTION',
                   'time_scope','CURRENT_MSK_DAY',
                   'count_unit','unique_symbol_side_strategy_timeframe_bar',
                   'sample_symbols',(
                       SELECT jsonb_agg(x.symbol ORDER BY x.rows_total DESC,x.symbol)
                       FROM (SELECT symbol,count(*) rows_total FROM admission_losses a2
                             WHERE a2.reason_value=a.reason_value
                             GROUP BY symbol ORDER BY count(*) DESC,symbol LIMIT 5) x
                   )) AS evidence_json
        FROM admission_losses a
        GROUP BY reason_value
        ORDER BY rows_total DESC,reason_value
    """)
    return [dict(row) for row in cur.fetchall()]


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
                json.dumps({
                    "mode": "linked_admission_loss_cohort",
                    "boundary": "RESEARCH_TO_EXECUTION",
                }, ensure_ascii=False),
            ))
            snapshot_id = int(cur.fetchone()["signal_funnel_reason_snapshot_id"])

            inserted = 0
            scanned_tables = 3
            scanned_columns = 2

            for row in collect_admission_losses(cur):
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
                    "analytics",
                    "signal_admission_loss_cohort_v3",
                    "rejection_reason_or_status",
                    value,
                    count,
                    reason_group(value),
                    json.dumps(row["evidence_json"], ensure_ascii=False),
                    SOURCE_VERSION,
                ))
                inserted += 1

    print("=== SIGNAL_FUNNEL_REASON_ANALYTICS_V1 ===")
    print(f"signal_funnel_reason_snapshot_id={snapshot_id}")
    print(f"scanned_tables={scanned_tables}")
    print(f"scanned_columns={scanned_columns}")
    print(f"reason_rows_inserted={inserted}")
    print("mode=linked_admission_loss_cohort")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=SIGNAL_FUNNEL_REASON_ANALYTICS_V1_READY")


if __name__ == "__main__":
    main()
