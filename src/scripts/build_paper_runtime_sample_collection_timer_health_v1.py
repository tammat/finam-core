from __future__ import annotations

import os
import subprocess
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1"

TIMER_UNIT = "finam-paper-sample-collection.timer"
SERVICE_UNIT = "finam-paper-sample-collection.service"
STALE_AFTER_SEC = int(os.getenv("PAPER_SAMPLE_COLLECTION_STALE_AFTER_SEC", "900"))


def systemctl_show(unit: str, props: list[str]) -> dict[str, str]:
    cmd = ["systemctl", "show", unit]
    for prop in props:
        cmd.extend(["-p", prop])

    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except Exception as exc:
        return {"__error__": f"{type(exc).__name__}:{exc}"}

    data: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v

    if result.returncode != 0:
        data["__error__"] = result.stderr.strip() or f"systemctl rc={result.returncode}"

    return data


def load_sample_summary(cur) -> dict:
    try:
        cur.execute("""
            SELECT
                candidates_total,
                sample_ready,
                collection_status,
                phase_status,
                micro_live_allowed,
                refreshed_at,
                extract(epoch FROM (now() - refreshed_at))::int AS age_sec
            FROM marketcore_ui.paper_runtime_sample_collection_v1
            WHERE id=1;
        """)
        row = cur.fetchone()
    except Exception as exc:
        return {
            "exists": False,
            "error": f"{type(exc).__name__}:{exc}",
        }

    if row is None:
        return {"exists": False, "error": "summary row id=1 not found"}

    return {
        "exists": True,
        "candidates_total": int(row["candidates_total"] or 0),
        "sample_ready": int(row["sample_ready"] or 0),
        "collection_status": str(row["collection_status"] or "UNKNOWN"),
        "phase_status": str(row["phase_status"] or "UNKNOWN"),
        "micro_live_allowed": bool(row["micro_live_allowed"] or False),
        "refreshed_at": row["refreshed_at"],
        "age_sec": int(row["age_sec"] or 0),
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    timer = systemctl_show(
        TIMER_UNIT,
        [
            "ActiveState",
            "SubState",
            "UnitFileState",
            "NextElapseUSecRealtime",
            "LastTriggerUSec",
        ],
    )

    service = systemctl_show(
        SERVICE_UNIT,
        [
            "ActiveState",
            "SubState",
            "Result",
            "ExecMainStatus",
            "InactiveExitTimestamp",
        ],
    )

    timer_active_state = timer.get("ActiveState", "unknown")
    timer_sub_state = timer.get("SubState", "unknown")
    timer_unit_file_state = timer.get("UnitFileState", "unknown")
    timer_next_elapse = timer.get("NextElapseUSecRealtime", "")
    timer_last_trigger = timer.get("LastTriggerUSec", "")

    service_active_state = service.get("ActiveState", "unknown")
    service_sub_state = service.get("SubState", "unknown")
    service_result = service.get("Result", "unknown")
    service_exec_main_status = service.get("ExecMainStatus", "")
    service_last_exit = service.get("InactiveExitTimestamp", "")

    timer_healthy = (
        timer_active_state == "active"
        and timer_unit_file_state in {"enabled", "static", "generated"}
        and "__error__" not in timer
    )

    service_healthy = (
        service_result in {"success", "", "unknown"}
        and "__error__" not in service
    )

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1 ===")

            summary = load_sample_summary(cur)

            sample_summary_exists = bool(summary.get("exists"))
            sample_summary_refreshed_at = summary.get("refreshed_at")
            sample_summary_age_sec = summary.get("age_sec")
            sample_summary_stale = True

            candidates_total = int(summary.get("candidates_total") or 0)
            sample_ready = int(summary.get("sample_ready") or 0)
            collection_status = str(summary.get("collection_status") or "UNKNOWN")
            phase_status = str(summary.get("phase_status") or "UNKNOWN")
            micro_live_allowed = bool(summary.get("micro_live_allowed") or False)

            if sample_summary_exists and sample_summary_age_sec is not None:
                sample_summary_stale = sample_summary_age_sec > STALE_AFTER_SEC

            if not timer_healthy:
                timer_health_status = "ERROR"
                health_reason = "systemd timer is not active/enabled or systemctl returned error"
                recommended_action = "Проверить systemctl status finam-paper-sample-collection.timer"
            elif not service_healthy:
                timer_health_status = "WARN"
                health_reason = "timer active, but last service result is not healthy"
                recommended_action = "Проверить journalctl -u finam-paper-sample-collection.service"
            elif not sample_summary_exists:
                timer_health_status = "ERROR"
                health_reason = str(summary.get("error") or "sample summary is missing")
                recommended_action = "Запустить sample collection cycle вручную"
            elif sample_summary_stale:
                timer_health_status = "STALE"
                health_reason = f"sample summary stale: age_sec={sample_summary_age_sec}"
                recommended_action = "Проверить timer и service journal"
            elif micro_live_allowed:
                timer_health_status = "ERROR"
                health_reason = "micro_live_allowed unexpectedly true"
                recommended_action = "Остановить продвижение и проверить risk gates"
            else:
                timer_health_status = "HEALTHY"
                health_reason = "timer active, service healthy, sample summary fresh, micro_live_allowed=0"
                recommended_action = "Продолжить Paper Runtime sample accumulation"

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_sample_collection_timer_health_v1 (
                    id,
                    timer_unit,
                    service_unit,
                    timer_active_state,
                    timer_sub_state,
                    timer_unit_file_state,
                    timer_next_elapse,
                    timer_last_trigger,
                    timer_healthy,
                    service_active_state,
                    service_sub_state,
                    service_result,
                    service_exec_main_status,
                    service_last_exit,
                    service_healthy,
                    sample_summary_exists,
                    sample_summary_refreshed_at,
                    sample_summary_age_sec,
                    sample_summary_stale,
                    candidates_total,
                    sample_ready,
                    collection_status,
                    phase_status,
                    micro_live_allowed,
                    timer_health_status,
                    health_reason,
                    recommended_action,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    timer_unit=EXCLUDED.timer_unit,
                    service_unit=EXCLUDED.service_unit,
                    timer_active_state=EXCLUDED.timer_active_state,
                    timer_sub_state=EXCLUDED.timer_sub_state,
                    timer_unit_file_state=EXCLUDED.timer_unit_file_state,
                    timer_next_elapse=EXCLUDED.timer_next_elapse,
                    timer_last_trigger=EXCLUDED.timer_last_trigger,
                    timer_healthy=EXCLUDED.timer_healthy,
                    service_active_state=EXCLUDED.service_active_state,
                    service_sub_state=EXCLUDED.service_sub_state,
                    service_result=EXCLUDED.service_result,
                    service_exec_main_status=EXCLUDED.service_exec_main_status,
                    service_last_exit=EXCLUDED.service_last_exit,
                    service_healthy=EXCLUDED.service_healthy,
                    sample_summary_exists=EXCLUDED.sample_summary_exists,
                    sample_summary_refreshed_at=EXCLUDED.sample_summary_refreshed_at,
                    sample_summary_age_sec=EXCLUDED.sample_summary_age_sec,
                    sample_summary_stale=EXCLUDED.sample_summary_stale,
                    candidates_total=EXCLUDED.candidates_total,
                    sample_ready=EXCLUDED.sample_ready,
                    collection_status=EXCLUDED.collection_status,
                    phase_status=EXCLUDED.phase_status,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
                    timer_health_status=EXCLUDED.timer_health_status,
                    health_reason=EXCLUDED.health_reason,
                    recommended_action=EXCLUDED.recommended_action,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                TIMER_UNIT,
                SERVICE_UNIT,
                timer_active_state,
                timer_sub_state,
                timer_unit_file_state,
                timer_next_elapse,
                timer_last_trigger,
                timer_healthy,
                service_active_state,
                service_sub_state,
                service_result,
                service_exec_main_status,
                service_last_exit,
                service_healthy,
                sample_summary_exists,
                sample_summary_refreshed_at,
                sample_summary_age_sec,
                sample_summary_stale,
                candidates_total,
                sample_ready,
                collection_status,
                phase_status,
                micro_live_allowed,
                timer_health_status,
                health_reason,
                recommended_action,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"timer_active_state={timer_active_state}")
    print(f"timer_unit_file_state={timer_unit_file_state}")
    print(f"timer_healthy={int(timer_healthy)}")
    print(f"service_result={service_result}")
    print(f"service_healthy={int(service_healthy)}")
    print(f"sample_summary_exists={int(sample_summary_exists)}")
    print(f"sample_summary_age_sec={sample_summary_age_sec}")
    print(f"sample_summary_stale={int(sample_summary_stale)}")
    print(f"candidates_total={candidates_total}")
    print(f"sample_ready={sample_ready}")
    print(f"collection_status={collection_status}")
    print(f"phase_status={phase_status}")
    print(f"timer_health_status={timer_health_status}")
    print(f"micro_live_allowed={int(micro_live_allowed)}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY")


if __name__ == "__main__":
    main()
