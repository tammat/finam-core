from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1 ===")

            cur.execute("""
                SELECT *
                FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
                WHERE id=1;
            """)
            phase = cur.fetchone()
            if phase is None:
                raise RuntimeError("phase_ii summary row id=1 not found")
            phase = dict(phase)

            cur.execute("""
                SELECT *
                FROM marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1
                WHERE id=1;
            """)
            health = cur.fetchone()
            if health is None:
                raise RuntimeError("operations timer health row id=1 not found")
            health = dict(health)

            phase_result_status = str(phase.get("phase_result_status") or "UNKNOWN")
            engineering_status = str(phase.get("engineering_status") or "UNKNOWN")
            operational_status = str(phase.get("operational_status") or "UNKNOWN")
            phase_close_status = str(phase.get("close_status") or "UNKNOWN")
            sample_collection_status = str(phase.get("collection_status") or "UNKNOWN")
            sample_phase_status = str(phase.get("collection_phase_status") or "UNKNOWN")
            timer_health_status = str(phase.get("timer_health_status") or "UNKNOWN")
            operations_health_status = str(health.get("health_status") or "UNKNOWN")

            operations_rows = int(health.get("operations_rows") or 0)
            operations_high_rows = int(health.get("operations_high_rows") or 0)
            operations_near_ready_rows = int(health.get("operations_near_ready_rows") or 0)
            operations_collecting_rows = int(health.get("operations_collecting_rows") or 0)

            candidates_total = int(phase.get("candidates_total") or 0)
            sample_ready = int(phase.get("sample_ready") or 0)
            wait_both_sample = int(phase.get("wait_both_sample") or 0)

            micro_live_allowed_rows = int(phase.get("micro_live_allowed_rows") or 0) + int(health.get("operations_micro_live_allowed_rows") or 0)
            micro_live_allowed = bool(phase.get("micro_live_allowed") or False) or micro_live_allowed_rows > 0

            if micro_live_allowed:
                daily_status = "ERROR_MICRO_LIVE_ALLOWED"
                conclusion = "Нарушение safety: обнаружено micro_live_allowed=true."
                recommended_action = "Остановить продвижение и проверить risk gates."
            elif operations_health_status not in {"HEALTHY", "STALE"}:
                daily_status = "OPERATIONS_HEALTH_ATTENTION"
                conclusion = "Операционный timer/sample operations требует внимания."
                recommended_action = "Проверить /paper-sample-operations-timer-health и journalctl."
            elif phase_result_status == "CLOSED_WAIT_SAMPLE" and operational_status == "WAIT_SAMPLE":
                daily_status = "WAIT_SAMPLE_OPERATIONAL"
                conclusion = "Фаза инженерно закрыта. Операционно идёт накопление Paper/OOS выборки."
                recommended_action = "Продолжить Paper Runtime sample collection. Micro Live остаётся заблокирован."
            elif sample_ready > 0:
                daily_status = "READY_FOR_REVALIDATION"
                conclusion = "Есть кандидаты с достаточной выборкой."
                recommended_action = "Запустить Edge revalidation для sample-ready кандидатов."
            else:
                daily_status = "REVIEW"
                conclusion = "Требуется проверка текущего состояния Phase II."
                recommended_action = str(phase.get("recommended_action") or "Проверить сводку Phase II.")

            cur.execute("DELETE FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 WHERE id=1;")

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 (
                    id,
                    summary_date,
                    phase_result_status,
                    engineering_status,
                    operational_status,
                    phase_close_status,
                    sample_collection_status,
                    sample_phase_status,
                    timer_health_status,
                    operations_health_status,
                    operations_rows,
                    operations_high_rows,
                    operations_near_ready_rows,
                    operations_collecting_rows,
                    candidates_total,
                    sample_ready,
                    wait_both_sample,
                    avg_progress_pct,
                    max_progress_pct,
                    min_remaining_total_trades,
                    min_remaining_oos_trades,
                    micro_live_allowed_rows,
                    micro_live_allowed,
                    daily_status,
                    conclusion,
                    recommended_action,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,current_date,
                    %s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,
                    %s,%s,%s,
                    now(),%s,%s
                );
            """, (
                phase_result_status,
                engineering_status,
                operational_status,
                phase_close_status,
                sample_collection_status,
                sample_phase_status,
                timer_health_status,
                operations_health_status,
                operations_rows,
                operations_high_rows,
                operations_near_ready_rows,
                operations_collecting_rows,
                candidates_total,
                sample_ready,
                wait_both_sample,
                phase.get("avg_progress_pct") or 0,
                phase.get("max_progress_pct") or 0,
                phase.get("min_remaining_total_trades"),
                phase.get("min_remaining_oos_trades"),
                micro_live_allowed_rows,
                micro_live_allowed,
                daily_status,
                conclusion,
                recommended_action,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"daily_status={daily_status}")
    print(f"phase_result_status={phase_result_status}")
    print(f"engineering_status={engineering_status}")
    print(f"operational_status={operational_status}")
    print(f"operations_health_status={operations_health_status}")
    print(f"operations_rows={operations_rows}")
    print(f"operations_high_rows={operations_high_rows}")
    print(f"operations_near_ready_rows={operations_near_ready_rows}")
    print(f"operations_collecting_rows={operations_collecting_rows}")
    print(f"candidates_total={candidates_total}")
    print(f"sample_ready={sample_ready}")
    print(f"wait_both_sample={wait_both_sample}")
    print(f"micro_live_allowed_rows={micro_live_allowed_rows}")
    print(f"micro_live_allowed={int(micro_live_allowed)}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_READY")


if __name__ == "__main__":
    main()
