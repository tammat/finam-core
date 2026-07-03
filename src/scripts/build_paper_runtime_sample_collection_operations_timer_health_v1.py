from __future__ import annotations

import os
import subprocess
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1"

TIMER_UNIT = "finam-paper-sample-operations.timer"
SERVICE_UNIT = "finam-paper-sample-operations.service"
STALE_AFTER_SEC = int(os.getenv("PAPER_SAMPLE_OPERATIONS_STALE_AFTER_SEC", "900"))


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
            key, value = line.split("=", 1)
            data[key] = value

    if result.returncode != 0:
        data["__error__"] = result.stderr.strip() or f"systemctl rc={result.returncode}"

    return data


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
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1 ===")

            cur.execute("""
                SELECT
                    count(*) AS operations_rows,
                    count(*) FILTER (WHERE operation_priority='HIGH') AS operations_high_rows,
                    count(*) FILTER (WHERE operation_status='NEAR_SAMPLE_READY') AS operations_near_ready_rows,
                    count(*) FILTER (WHERE operation_status='COLLECTING') AS operations_collecting_rows,
                    count(*) FILTER (WHERE micro_live_allowed=true) AS operations_micro_live_allowed_rows,
                    max(refreshed_at) AS operations_refreshed_at,
                    extract(epoch FROM (now() - max(refreshed_at)))::int AS operations_age_sec
                FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;
            """)
            ops = dict(cur.fetchone())

            operations_rows = int(ops["operations_rows"] or 0)
            operations_high_rows = int(ops["operations_high_rows"] or 0)
            operations_near_ready_rows = int(ops["operations_near_ready_rows"] or 0)
            operations_collecting_rows = int(ops["operations_collecting_rows"] or 0)
            operations_micro_live_allowed_rows = int(ops["operations_micro_live_allowed_rows"] or 0)
            operations_refreshed_at = ops["operations_refreshed_at"]
            operations_age_sec = ops["operations_age_sec"]

            operations_stale = True
            if operations_refreshed_at is not None and operations_age_sec is not None:
                operations_stale = int(operations_age_sec) > STALE_AFTER_SEC

            cur.execute("""
                SELECT
                    phase_result_status,
                    engineering_status,
                    operational_status,
                    timer_health_status,
                    next_phase
                FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
                WHERE id=1;
            """)
            phase = cur.fetchone()

            if phase is None:
                phase_result_status = "UNKNOWN"
                engineering_status = "UNKNOWN"
                operational_status = "UNKNOWN"
                phase_timer_health_status = "UNKNOWN"
                next_phase = ""
            else:
                phase = dict(phase)
                phase_result_status = str(phase.get("phase_result_status") or "UNKNOWN")
                engineering_status = str(phase.get("engineering_status") or "UNKNOWN")
                operational_status = str(phase.get("operational_status") or "UNKNOWN")
                phase_timer_health_status = str(phase.get("timer_health_status") or "UNKNOWN")
                next_phase = str(phase.get("next_phase") or "")

            micro_live_allowed = operations_micro_live_allowed_rows > 0

            if micro_live_allowed:
                health_status = "ERROR"
                health_reason = "operations layer has micro_live_allowed=true"
                recommended_action = "Остановить продвижение и проверить risk gates."
            elif not timer_healthy:
                health_status = "ERROR"
                health_reason = "operations timer is not active/enabled or systemctl returned error"
                recommended_action = "Проверить systemctl status finam-paper-sample-operations.timer"
            elif not service_healthy:
                health_status = "WARN"
                health_reason = "operations timer active, but last service result is not healthy"
                recommended_action = "Проверить journalctl -u finam-paper-sample-operations.service"
            elif operations_rows <= 0:
                health_status = "ERROR"
                health_reason = "operations table is empty"
                recommended_action = "Запустить finam-paper-sample-operations.service вручную."
            elif operations_stale:
                health_status = "STALE"
                health_reason = f"operations summary stale: age_sec={operations_age_sec}"
                recommended_action = "Проверить operations timer и service journal."
            else:
                health_status = "HEALTHY"
                health_reason = "operations timer active, service healthy, operations fresh, micro_live_allowed=0"
                recommended_action = "Продолжить Paper Runtime sample collection operations."

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1 (
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
                    operations_rows,
                    operations_high_rows,
                    operations_near_ready_rows,
                    operations_collecting_rows,
                    operations_micro_live_allowed_rows,
                    operations_refreshed_at,
                    operations_age_sec,
                    operations_stale,
                    phase_result_status,
                    engineering_status,
                    operational_status,
                    phase_timer_health_status,
                    next_phase,
                    health_status,
                    health_reason,
                    recommended_action,
                    micro_live_allowed,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    now(),%s,%s
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
                    operations_rows=EXCLUDED.operations_rows,
                    operations_high_rows=EXCLUDED.operations_high_rows,
                    operations_near_ready_rows=EXCLUDED.operations_near_ready_rows,
                    operations_collecting_rows=EXCLUDED.operations_collecting_rows,
                    operations_micro_live_allowed_rows=EXCLUDED.operations_micro_live_allowed_rows,
                    operations_refreshed_at=EXCLUDED.operations_refreshed_at,
                    operations_age_sec=EXCLUDED.operations_age_sec,
                    operations_stale=EXCLUDED.operations_stale,
                    phase_result_status=EXCLUDED.phase_result_status,
                    engineering_status=EXCLUDED.engineering_status,
                    operational_status=EXCLUDED.operational_status,
                    phase_timer_health_status=EXCLUDED.phase_timer_health_status,
                    next_phase=EXCLUDED.next_phase,
                    health_status=EXCLUDED.health_status,
                    health_reason=EXCLUDED.health_reason,
                    recommended_action=EXCLUDED.recommended_action,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
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
                operations_rows,
                operations_high_rows,
                operations_near_ready_rows,
                operations_collecting_rows,
                operations_micro_live_allowed_rows,
                operations_refreshed_at,
                operations_age_sec,
                operations_stale,
                phase_result_status,
                engineering_status,
                operational_status,
                phase_timer_health_status,
                next_phase,
                health_status,
                health_reason,
                recommended_action,
                micro_live_allowed,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"timer_active_state={timer_active_state}")
    print(f"timer_unit_file_state={timer_unit_file_state}")
    print(f"timer_healthy={int(timer_healthy)}")
    print(f"service_result={service_result}")
    print(f"service_healthy={int(service_healthy)}")
    print(f"operations_rows={operations_rows}")
    print(f"operations_high_rows={operations_high_rows}")
    print(f"operations_near_ready_rows={operations_near_ready_rows}")
    print(f"operations_collecting_rows={operations_collecting_rows}")
    print(f"operations_micro_live_allowed_rows={operations_micro_live_allowed_rows}")
    print(f"operations_age_sec={operations_age_sec}")
    print(f"operations_stale={int(operations_stale)}")
    print(f"phase_result_status={phase_result_status}")
    print(f"engineering_status={engineering_status}")
    print(f"operational_status={operational_status}")
    print(f"health_status={health_status}")
    print(f"micro_live_allowed={int(micro_live_allowed)}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1_READY")


if __name__ == "__main__":
    main()
