from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1 ===")

            cur.execute("""
                SELECT
                    candidates_total,
                    sample_ready,
                    wait_both_sample,
                    wait_total_sample,
                    wait_oos_sample,
                    min_remaining_total_trades,
                    min_remaining_oos_trades,
                    avg_progress_pct,
                    max_progress_pct,
                    collection_status,
                    phase_status,
                    micro_live_allowed
                FROM marketcore_ui.paper_runtime_sample_collection_v1
                WHERE id=1;
            """)
            collection = cur.fetchone()
            if collection is None:
                raise RuntimeError("marketcore_ui.paper_runtime_sample_collection_v1 id=1 not found")

            collection = dict(collection)

            cur.execute("""
                SELECT
                    timer_health_status,
                    timer_healthy,
                    service_healthy,
                    sample_summary_stale,
                    sample_summary_age_sec,
                    micro_live_allowed
                FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
                WHERE id=1;
            """)
            timer = cur.fetchone()
            if timer is None:
                raise RuntimeError("marketcore_ui.paper_runtime_sample_collection_timer_health_v1 id=1 not found")

            timer = dict(timer)

            cur.execute("""
                SELECT count(*) AS ready_rows
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_ready=true;
            """)
            micro_live_ready_rows = int(cur.fetchone()["ready_rows"] or 0)

            cur.execute("""
                SELECT count(*) AS allowed_rows
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_allowed=true;
            """)
            micro_live_allowed_rows = int(cur.fetchone()["allowed_rows"] or 0)

            candidates_total = int(collection["candidates_total"] or 0)
            sample_ready = int(collection["sample_ready"] or 0)
            wait_both_sample = int(collection["wait_both_sample"] or 0)
            wait_total_sample = int(collection["wait_total_sample"] or 0)
            wait_oos_sample = int(collection["wait_oos_sample"] or 0)

            timer_health_status = str(timer["timer_health_status"] or "UNKNOWN")
            timer_healthy = bool(timer["timer_healthy"] or False)
            service_healthy = bool(timer["service_healthy"] or False)
            sample_summary_stale = bool(timer["sample_summary_stale"] or False)
            micro_live_allowed = bool(collection["micro_live_allowed"] or False) or micro_live_allowed_rows > 0

            if micro_live_allowed:
                engineering_status = "BLOCKED"
                operational_status = "ERROR"
                close_status = "FAILED"
                close_reason = "micro_live_allowed unexpectedly true"
                recommended_action = "Остановить продвижение и проверить risk gates."
                next_phase = "MANUAL_RISK_REVIEW_REQUIRED"
            elif not timer_healthy or not service_healthy or timer_health_status not in {"HEALTHY", "STALE"}:
                engineering_status = "BLOCKED"
                operational_status = "TIMER_UNHEALTHY"
                close_status = "FAILED"
                close_reason = "sample collection timer/service unhealthy"
                recommended_action = "Проверить timer health и journalctl."
                next_phase = "TIMER_HEALTH_FIX"
            elif sample_summary_stale:
                engineering_status = "BLOCKED"
                operational_status = "STALE_SAMPLE_SUMMARY"
                close_status = "FAILED"
                close_reason = "sample summary is stale"
                recommended_action = "Запустить paper sample collection cycle вручную и проверить timer."
                next_phase = "TIMER_HEALTH_FIX"
            elif candidates_total <= 0:
                engineering_status = "CLOSED"
                operational_status = "NO_CANDIDATES"
                close_status = "CLOSED_NO_CANDIDATES"
                close_reason = "phase infrastructure is ready, but no candidates exist"
                recommended_action = "Продолжить Paper Runtime и Research Candidate generation."
                next_phase = "PAPER_RUNTIME_SAMPLE_COLLECTION"
            elif sample_ready > 0:
                engineering_status = "CLOSED"
                operational_status = "READY_FOR_REVALIDATION"
                close_status = "CLOSED_READY_FOR_REVALIDATION"
                close_reason = "one or more candidates reached minimum sample thresholds"
                recommended_action = "Перезапустить Edge Validation Pipeline для sample-ready кандидатов."
                next_phase = "EDGE_REVALIDATION_ON_SAMPLE_READY"
            else:
                engineering_status = "CLOSED"
                operational_status = "WAIT_SAMPLE"
                close_status = "CLOSED_WAIT_SAMPLE"
                close_reason = "phase is complete; candidates are waiting for Paper/OOS sample accumulation"
                recommended_action = "Продолжить Paper Runtime sample accumulation. Micro Live remains blocked."
                next_phase = "PAPER_RUNTIME_SAMPLE_COLLECTION"

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_sample_collection_phase_close_v1 (
                    id,
                    phase_name,
                    engineering_status,
                    operational_status,
                    candidates_total,
                    sample_ready,
                    wait_both_sample,
                    wait_total_sample,
                    wait_oos_sample,
                    min_remaining_total_trades,
                    min_remaining_oos_trades,
                    avg_progress_pct,
                    max_progress_pct,
                    collection_status,
                    collection_phase_status,
                    timer_health_status,
                    timer_healthy,
                    service_healthy,
                    sample_summary_stale,
                    sample_summary_age_sec,
                    micro_live_ready_rows,
                    micro_live_allowed_rows,
                    micro_live_allowed,
                    close_status,
                    close_reason,
                    recommended_action,
                    next_phase,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,
                    now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    phase_name=EXCLUDED.phase_name,
                    engineering_status=EXCLUDED.engineering_status,
                    operational_status=EXCLUDED.operational_status,
                    candidates_total=EXCLUDED.candidates_total,
                    sample_ready=EXCLUDED.sample_ready,
                    wait_both_sample=EXCLUDED.wait_both_sample,
                    wait_total_sample=EXCLUDED.wait_total_sample,
                    wait_oos_sample=EXCLUDED.wait_oos_sample,
                    min_remaining_total_trades=EXCLUDED.min_remaining_total_trades,
                    min_remaining_oos_trades=EXCLUDED.min_remaining_oos_trades,
                    avg_progress_pct=EXCLUDED.avg_progress_pct,
                    max_progress_pct=EXCLUDED.max_progress_pct,
                    collection_status=EXCLUDED.collection_status,
                    collection_phase_status=EXCLUDED.collection_phase_status,
                    timer_health_status=EXCLUDED.timer_health_status,
                    timer_healthy=EXCLUDED.timer_healthy,
                    service_healthy=EXCLUDED.service_healthy,
                    sample_summary_stale=EXCLUDED.sample_summary_stale,
                    sample_summary_age_sec=EXCLUDED.sample_summary_age_sec,
                    micro_live_ready_rows=EXCLUDED.micro_live_ready_rows,
                    micro_live_allowed_rows=EXCLUDED.micro_live_allowed_rows,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
                    close_status=EXCLUDED.close_status,
                    close_reason=EXCLUDED.close_reason,
                    recommended_action=EXCLUDED.recommended_action,
                    next_phase=EXCLUDED.next_phase,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                "PAPER_RUNTIME_SAMPLE_COLLECTION",
                engineering_status,
                operational_status,
                candidates_total,
                sample_ready,
                wait_both_sample,
                wait_total_sample,
                wait_oos_sample,
                collection["min_remaining_total_trades"],
                collection["min_remaining_oos_trades"],
                collection["avg_progress_pct"],
                collection["max_progress_pct"],
                collection["collection_status"],
                collection["phase_status"],
                timer_health_status,
                timer_healthy,
                service_healthy,
                sample_summary_stale,
                timer["sample_summary_age_sec"],
                micro_live_ready_rows,
                micro_live_allowed_rows,
                micro_live_allowed,
                close_status,
                close_reason,
                recommended_action,
                next_phase,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"engineering_status={engineering_status}")
    print(f"operational_status={operational_status}")
    print(f"close_status={close_status}")
    print(f"candidates_total={candidates_total}")
    print(f"sample_ready={sample_ready}")
    print(f"wait_both_sample={wait_both_sample}")
    print(f"timer_health_status={timer_health_status}")
    print(f"micro_live_ready_rows={micro_live_ready_rows}")
    print(f"micro_live_allowed_rows={micro_live_allowed_rows}")
    print(f"micro_live_allowed={int(micro_live_allowed)}")
    print(f"next_phase={next_phase}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_READY")


if __name__ == "__main__":
    main()
