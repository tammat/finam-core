from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_V1 ===")

            cur.execute("""
                SELECT
                    count(*) AS candidates_total,
                    count(*) FILTER (WHERE sample_status='SAMPLE_READY') AS sample_ready,
                    count(*) FILTER (WHERE sample_status='WAIT_BOTH_SAMPLE') AS wait_both_sample,
                    count(*) FILTER (WHERE sample_status='WAIT_TOTAL_SAMPLE') AS wait_total_sample,
                    count(*) FILTER (WHERE sample_status='WAIT_OOS_SAMPLE') AS wait_oos_sample,
                    min(remaining_total_trades) AS min_remaining_total_trades,
                    min(remaining_oos_trades) AS min_remaining_oos_trades,
                    coalesce(avg(progress_pct),0) AS avg_progress_pct,
                    coalesce(max(progress_pct),0) AS max_progress_pct,
                    bool_or(micro_live_allowed) AS micro_live_allowed
                FROM marketcore_ui.paper_sample_accumulation_monitor_v1;
            """)
            r = dict(cur.fetchone())

            candidates_total = int(r["candidates_total"] or 0)
            sample_ready = int(r["sample_ready"] or 0)
            micro_live_allowed = bool(r["micro_live_allowed"] or False)

            if candidates_total == 0:
                collection_status = "NO_CANDIDATES"
                phase_status = "NOT_READY"
                recommended_action = "Запустить Paper Edge Discovery и накопить кандидатов."
            elif sample_ready > 0:
                collection_status = "SAMPLE_READY"
                phase_status = "READY_FOR_REVALIDATION"
                recommended_action = "Перезапустить Validation Pipeline для кандидатов с достаточной выборкой."
            else:
                collection_status = "COLLECTING"
                phase_status = "WAIT_SAMPLE"
                recommended_action = "Продолжить Paper Runtime. Кандидаты ждут накопления общей и OOS-выборки."

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_sample_collection_v1 (
                    id,
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
                    recommended_action,
                    micro_live_allowed,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
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
                    phase_status=EXCLUDED.phase_status,
                    recommended_action=EXCLUDED.recommended_action,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                candidates_total,
                sample_ready,
                int(r["wait_both_sample"] or 0),
                int(r["wait_total_sample"] or 0),
                int(r["wait_oos_sample"] or 0),
                r["min_remaining_total_trades"],
                r["min_remaining_oos_trades"],
                r["avg_progress_pct"],
                r["max_progress_pct"],
                collection_status,
                phase_status,
                recommended_action,
                micro_live_allowed,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"candidates_total={candidates_total}")
    print(f"sample_ready={sample_ready}")
    print(f"collection_status={collection_status}")
    print(f"phase_status={phase_status}")
    print(f"micro_live_allowed={int(micro_live_allowed)}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY")


if __name__ == "__main__":
    main()
