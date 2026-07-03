from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict, timer_health_status: str, collection_status: str, phase_status: str) -> dict:
    remaining_total = int(row.get("remaining_total_trades") or 0)
    remaining_oos = int(row.get("remaining_oos_trades") or 0)
    progress_pct = dec(row.get("progress_pct"))
    sample_status = str(row.get("sample_status") or "UNKNOWN")
    micro_live_allowed = bool(row.get("micro_live_allowed") or False)

    if micro_live_allowed:
        return {
            "operation_priority": "CRITICAL",
            "operation_status": "BLOCKED_MICRO_LIVE_ALLOWED",
            "operation_reason": "micro_live_allowed unexpectedly true",
            "recommended_action": "Остановить продвижение и проверить risk gates.",
            "next_check": "MANUAL_RISK_REVIEW",
        }

    if timer_health_status not in {"HEALTHY", "STALE"}:
        return {
            "operation_priority": "CRITICAL",
            "operation_status": "TIMER_HEALTH_REQUIRED",
            "operation_reason": "sample collection timer/service unhealthy",
            "recommended_action": "Проверить timer health и journalctl.",
            "next_check": "PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1",
        }

    if sample_status == "SAMPLE_READY":
        return {
            "operation_priority": "HIGH",
            "operation_status": "READY_FOR_REVALIDATION",
            "operation_reason": "минимальная выборка набрана",
            "recommended_action": "Перезапустить Edge Validation Pipeline для кандидата.",
            "next_check": "EDGE_REVALIDATION_ON_SAMPLE_READY",
        }

    if remaining_total <= 5 and remaining_oos <= 3:
        return {
            "operation_priority": "HIGH",
            "operation_status": "NEAR_SAMPLE_READY",
            "operation_reason": "кандидат близок к минимальной выборке",
            "recommended_action": "Продолжить Paper Runtime и проверить кандидата после ближайших сделок.",
            "next_check": "PAPER_SAMPLE_ACCUMULATION_MONITOR_V1",
        }

    if progress_pct >= Decimal("70"):
        return {
            "operation_priority": "NORMAL",
            "operation_status": "ACCUMULATING_FAST",
            "operation_reason": "прогресс выборки выше 70%",
            "recommended_action": "Продолжить накопление выборки.",
            "next_check": "PAPER_SAMPLE_ACCUMULATION_MONITOR_V1",
        }

    if collection_status == "COLLECTING" and phase_status == "WAIT_SAMPLE":
        return {
            "operation_priority": "NORMAL",
            "operation_status": "COLLECTING",
            "operation_reason": "кандидат ожидает накопления Paper/OOS выборки",
            "recommended_action": "Продолжить Paper Runtime sample accumulation.",
            "next_check": "PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1",
        }

    return {
        "operation_priority": "LOW",
        "operation_status": "OBSERVE",
        "operation_reason": "операционный статус требует наблюдения",
        "recommended_action": "Проверить summary и monitor.",
        "next_check": "PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1",
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1 ===")

            cur.execute("""
                SELECT
                    timer_health_status,
                    collection_status,
                    phase_status,
                    micro_live_allowed
                FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
                WHERE id=1;
            """)
            health = cur.fetchone()
            if health is None:
                raise RuntimeError("timer health row id=1 not found")

            health = dict(health)
            timer_health_status = str(health.get("timer_health_status") or "UNKNOWN")

            cur.execute("""
                SELECT
                    collection_status,
                    phase_status
                FROM marketcore_ui.paper_runtime_sample_collection_v1
                WHERE id=1;
            """)
            summary = cur.fetchone()
            if summary is None:
                raise RuntimeError("sample collection summary id=1 not found")

            summary = dict(summary)
            collection_status = str(summary.get("collection_status") or "UNKNOWN")
            phase_status = str(summary.get("phase_status") or "UNKNOWN")

            cur.execute("""
                SELECT
                    monitor_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    readiness_status,
                    backtest_status,
                    oos_status,
                    robustness_status,
                    total_trades,
                    required_total_trades,
                    remaining_total_trades,
                    oos_trades,
                    required_oos_trades,
                    remaining_oos_trades,
                    sample_status,
                    progress_pct,
                    micro_live_ready,
                    micro_live_allowed,
                    recommended_action
                FROM marketcore_ui.paper_sample_accumulation_monitor_v1
                ORDER BY
                    CASE
                        WHEN sample_status='SAMPLE_READY' THEN 1
                        WHEN remaining_total_trades <= 5 AND remaining_oos_trades <= 3 THEN 2
                        WHEN progress_pct >= 70 THEN 3
                        ELSE 4
                    END,
                    remaining_total_trades,
                    remaining_oos_trades,
                    monitor_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row, timer_health_status, collection_status, phase_status)

                cur.execute("""
                    INSERT INTO marketcore_ui.paper_runtime_sample_collection_operations_v1 (
                        operation_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        sample_status,
                        readiness_status,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        total_trades,
                        required_total_trades,
                        remaining_total_trades,
                        oos_trades,
                        required_oos_trades,
                        remaining_oos_trades,
                        progress_pct,
                        operation_priority,
                        operation_status,
                        operation_reason,
                        recommended_action,
                        next_check,
                        timer_health_status,
                        collection_status,
                        phase_status,
                        micro_live_ready,
                        micro_live_allowed,
                        source_monitor_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("sample_status") or "UNKNOWN",
                    row.get("readiness_status") or "UNKNOWN",
                    row.get("backtest_status") or "UNKNOWN",
                    row.get("oos_status") or "UNKNOWN",
                    row.get("robustness_status") or "UNKNOWN",
                    row.get("total_trades") or 0,
                    row.get("required_total_trades") or 30,
                    row.get("remaining_total_trades") or 0,
                    row.get("oos_trades") or 0,
                    row.get("required_oos_trades") or 10,
                    row.get("remaining_oos_trades") or 0,
                    row.get("progress_pct") or 0,
                    c["operation_priority"],
                    c["operation_status"],
                    c["operation_reason"],
                    c["recommended_action"],
                    c["next_check"],
                    timer_health_status,
                    collection_status,
                    phase_status,
                    bool(row.get("micro_live_ready") or False),
                    bool(row.get("micro_live_allowed") or False),
                    row.get("monitor_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT operation_status, count(*) AS rows
                FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
                GROUP BY operation_status
                ORDER BY operation_status;
            """)
            status_rows = cur.fetchall()

            cur.execute("""
                SELECT count(*) AS allowed
                FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
                WHERE micro_live_allowed=true;
            """)
            allowed_rows = int(cur.fetchone()["allowed"])

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"operation_status_{row['operation_status']}={row['rows']}")
    print(f"micro_live_allowed_rows={allowed_rows}")
    print(f"timer_health_status={timer_health_status}")
    print(f"collection_status={collection_status}")
    print(f"phase_status={phase_status}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_READY")


if __name__ == "__main__":
    main()
