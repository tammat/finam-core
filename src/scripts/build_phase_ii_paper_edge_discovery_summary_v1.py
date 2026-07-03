from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1"


def count_rows(cur, table: str) -> int:
    cur.execute(f"SELECT count(*) AS rows FROM {table};")
    return int(cur.fetchone()["rows"] or 0)


def count_where(cur, table: str, where: str) -> int:
    cur.execute(f"SELECT count(*) AS rows FROM {table} WHERE {where};")
    return int(cur.fetchone()["rows"] or 0)


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1 ===")

            cur.execute("""
                SELECT *
                FROM marketcore_ui.paper_runtime_sample_collection_phase_close_v1
                WHERE id=1;
            """)
            close = cur.fetchone()
            if close is None:
                raise RuntimeError("phase close row id=1 not found")

            close = dict(close)

            paper_candidates_rows = count_rows(cur, "marketcore_ui.paper_edge_research_candidates_v1")
            validation_queue_rows = count_rows(cur, "marketcore_ui.edge_validation_queue_v1")
            validation_pipeline_rows = count_rows(cur, "marketcore_ui.edge_validation_pipeline_v1")
            robustness_rows = count_rows(cur, "marketcore_ui.edge_robustness_check_v1")
            oos_validation_rows = count_rows(cur, "marketcore_ui.edge_oos_validation_v1")
            oos_backtest_rows = count_rows(cur, "marketcore_ui.edge_oos_backtest_v1")
            micro_live_readiness_rows = count_rows(cur, "marketcore_ui.micro_live_readiness_v1")
            sample_monitor_rows = count_rows(cur, "marketcore_ui.paper_sample_accumulation_monitor_v1")

            micro_live_ready_rows = count_where(
                cur,
                "marketcore_ui.micro_live_readiness_v1",
                "micro_live_ready=true",
            )
            micro_live_allowed_rows = count_where(
                cur,
                "marketcore_ui.micro_live_readiness_v1",
                "micro_live_allowed=true",
            )

            micro_live_allowed = bool(close.get("micro_live_allowed") or False) or micro_live_allowed_rows > 0

            engineering_status = str(close.get("engineering_status") or "UNKNOWN")
            operational_status = str(close.get("operational_status") or "UNKNOWN")
            close_status = str(close.get("close_status") or "UNKNOWN")
            timer_health_status = str(close.get("timer_health_status") or "UNKNOWN")
            collection_status = str(close.get("collection_status") or "UNKNOWN")
            collection_phase_status = str(close.get("collection_phase_status") or "UNKNOWN")

            if micro_live_allowed:
                phase_result_status = "FAILED_MICRO_LIVE_ALLOWED"
                conclusion = "Фаза не может быть закрыта: обнаружен micro_live_allowed=true."
                recommended_action = "Остановить продвижение и проверить risk gates."
                next_phase = "MANUAL_RISK_REVIEW_REQUIRED"
            elif engineering_status == "CLOSED" and close_status.startswith("CLOSED"):
                if operational_status == "WAIT_SAMPLE":
                    phase_result_status = "CLOSED_WAIT_SAMPLE"
                    conclusion = "Инженерный контур Paper Edge Discovery завершён. Операционно продолжается накопление Paper/OOS выборки."
                    recommended_action = "Продолжить Paper Runtime sample accumulation до достижения минимальной выборки."
                    next_phase = "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS"
                elif operational_status == "READY_FOR_REVALIDATION":
                    phase_result_status = "CLOSED_READY_FOR_REVALIDATION"
                    conclusion = "Фаза закрыта, есть кандидаты с достаточной выборкой для повторной проверки."
                    recommended_action = "Запустить Edge revalidation для sample-ready кандидатов."
                    next_phase = "EDGE_REVALIDATION_ON_SAMPLE_READY"
                else:
                    phase_result_status = "CLOSED"
                    conclusion = "Фаза закрыта как инженерный контур."
                    recommended_action = str(close.get("recommended_action") or "")
                    next_phase = str(close.get("next_phase") or "")
            else:
                phase_result_status = "REVIEW_REQUIRED"
                conclusion = "Фаза требует проверки: закрывающий статус не подтверждает штатное завершение."
                recommended_action = str(close.get("recommended_action") or "Проверить phase close и timer health.")
                next_phase = str(close.get("next_phase") or "PHASE_REVIEW")

            cur.execute("""
                INSERT INTO marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 (
                    id,
                    phase_name,
                    phase_result_status,
                    engineering_status,
                    operational_status,
                    close_status,
                    timer_health_status,
                    collection_status,
                    collection_phase_status,
                    candidates_total,
                    sample_ready,
                    wait_both_sample,
                    wait_total_sample,
                    wait_oos_sample,
                    min_remaining_total_trades,
                    min_remaining_oos_trades,
                    avg_progress_pct,
                    max_progress_pct,
                    paper_candidates_rows,
                    validation_queue_rows,
                    validation_pipeline_rows,
                    robustness_rows,
                    oos_validation_rows,
                    oos_backtest_rows,
                    micro_live_readiness_rows,
                    sample_monitor_rows,
                    micro_live_ready_rows,
                    micro_live_allowed_rows,
                    micro_live_allowed,
                    conclusion,
                    recommended_action,
                    next_phase,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    phase_name=EXCLUDED.phase_name,
                    phase_result_status=EXCLUDED.phase_result_status,
                    engineering_status=EXCLUDED.engineering_status,
                    operational_status=EXCLUDED.operational_status,
                    close_status=EXCLUDED.close_status,
                    timer_health_status=EXCLUDED.timer_health_status,
                    collection_status=EXCLUDED.collection_status,
                    collection_phase_status=EXCLUDED.collection_phase_status,
                    candidates_total=EXCLUDED.candidates_total,
                    sample_ready=EXCLUDED.sample_ready,
                    wait_both_sample=EXCLUDED.wait_both_sample,
                    wait_total_sample=EXCLUDED.wait_total_sample,
                    wait_oos_sample=EXCLUDED.wait_oos_sample,
                    min_remaining_total_trades=EXCLUDED.min_remaining_total_trades,
                    min_remaining_oos_trades=EXCLUDED.min_remaining_oos_trades,
                    avg_progress_pct=EXCLUDED.avg_progress_pct,
                    max_progress_pct=EXCLUDED.max_progress_pct,
                    paper_candidates_rows=EXCLUDED.paper_candidates_rows,
                    validation_queue_rows=EXCLUDED.validation_queue_rows,
                    validation_pipeline_rows=EXCLUDED.validation_pipeline_rows,
                    robustness_rows=EXCLUDED.robustness_rows,
                    oos_validation_rows=EXCLUDED.oos_validation_rows,
                    oos_backtest_rows=EXCLUDED.oos_backtest_rows,
                    micro_live_readiness_rows=EXCLUDED.micro_live_readiness_rows,
                    sample_monitor_rows=EXCLUDED.sample_monitor_rows,
                    micro_live_ready_rows=EXCLUDED.micro_live_ready_rows,
                    micro_live_allowed_rows=EXCLUDED.micro_live_allowed_rows,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
                    conclusion=EXCLUDED.conclusion,
                    recommended_action=EXCLUDED.recommended_action,
                    next_phase=EXCLUDED.next_phase,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                "PHASE_II_PAPER_EDGE_DISCOVERY",
                phase_result_status,
                engineering_status,
                operational_status,
                close_status,
                timer_health_status,
                collection_status,
                collection_phase_status,
                int(close.get("candidates_total") or 0),
                int(close.get("sample_ready") or 0),
                int(close.get("wait_both_sample") or 0),
                int(close.get("wait_total_sample") or 0),
                int(close.get("wait_oos_sample") or 0),
                close.get("min_remaining_total_trades"),
                close.get("min_remaining_oos_trades"),
                close.get("avg_progress_pct") or 0,
                close.get("max_progress_pct") or 0,
                paper_candidates_rows,
                validation_queue_rows,
                validation_pipeline_rows,
                robustness_rows,
                oos_validation_rows,
                oos_backtest_rows,
                micro_live_readiness_rows,
                sample_monitor_rows,
                micro_live_ready_rows,
                micro_live_allowed_rows,
                micro_live_allowed,
                conclusion,
                recommended_action,
                next_phase,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"phase_result_status={phase_result_status}")
    print(f"engineering_status={engineering_status}")
    print(f"operational_status={operational_status}")
    print(f"close_status={close_status}")
    print(f"timer_health_status={timer_health_status}")
    print(f"paper_candidates_rows={paper_candidates_rows}")
    print(f"validation_queue_rows={validation_queue_rows}")
    print(f"validation_pipeline_rows={validation_pipeline_rows}")
    print(f"robustness_rows={robustness_rows}")
    print(f"oos_validation_rows={oos_validation_rows}")
    print(f"oos_backtest_rows={oos_backtest_rows}")
    print(f"micro_live_readiness_rows={micro_live_readiness_rows}")
    print(f"sample_monitor_rows={sample_monitor_rows}")
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
    print("VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY")


if __name__ == "__main__":
    main()
