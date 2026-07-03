from __future__ import annotations

import os
import socket
import subprocess
import uuid
from urllib.request import urlopen

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1"

KG_API_UNIT = "marketcore-kg-api.service"
UI_SHELL_UNIT = "marketcore-ui-shell.service"
KG_API_PORT = 8095
UI_SHELL_PORT = 8080


def systemctl_show(unit: str) -> dict[str, str]:
    props = ["ActiveState", "SubState", "Result", "ExecMainStatus"]
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


def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_contains(url: str, token: str, timeout: float = 3.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
        return token in body
    except Exception:
        return False


def get_server_ip() -> str:
    try:
        result = subprocess.run(
            ["hostname", "-I"],
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
        return result.stdout.split()[0]
    except Exception:
        return "127.0.0.1"


def main() -> None:
    build_id = str(uuid.uuid4())

    kg = systemctl_show(KG_API_UNIT)
    ui = systemctl_show(UI_SHELL_UNIT)

    kg_api_active_state = kg.get("ActiveState", "unknown")
    kg_api_sub_state = kg.get("SubState", "unknown")
    kg_api_result = kg.get("Result", "unknown")
    kg_api_main_status = kg.get("ExecMainStatus", "")

    ui_shell_active_state = ui.get("ActiveState", "unknown")
    ui_shell_sub_state = ui.get("SubState", "unknown")
    ui_shell_result = ui.get("Result", "unknown")
    ui_shell_main_status = ui.get("ExecMainStatus", "")

    kg_api_healthy = (
        kg_api_active_state == "active"
        and kg_api_result in {"success", "", "unknown"}
        and "__error__" not in kg
    )

    ui_shell_healthy = (
        ui_shell_active_state == "active"
        and ui_shell_result in {"success", "", "unknown"}
        and "__error__" not in ui
    )

    kg_port_ok = port_open("127.0.0.1", KG_API_PORT)
    ui_port_ok = port_open("127.0.0.1", UI_SHELL_PORT)

    kg_api_http_ok = http_contains("http://127.0.0.1:8095/api/kg/v1/health", '"status": "OK"')
    ui_home_http_ok = http_contains("http://127.0.0.1:8080/", "MarketCore OS")
    ui_risk_http_ok = http_contains("http://127.0.0.1:8080/risk", "Риски")
    ui_settings_http_ok = http_contains("http://127.0.0.1:8080/settings", "Настройки")

    kg_api_health_status = "HEALTHY" if kg_api_healthy and kg_port_ok and kg_api_http_ok else "ERROR"
    ui_shell_health_status = "HEALTHY" if ui_shell_healthy and ui_port_ok and ui_home_http_ok and ui_risk_http_ok and ui_settings_http_ok else "ERROR"

    server_ip = get_server_ip()
    open_url = f"http://{server_ip}:8080/"
    risk_url = f"http://{server_ip}:8080/risk"
    settings_url = f"http://{server_ip}:8080/settings"

    if kg_api_health_status != "HEALTHY":
        overall_status = "ERROR"
        health_reason = "KG API service/port/http health failed"
        recommended_action = "Проверить systemctl status marketcore-kg-api.service и journalctl."
    elif ui_shell_health_status != "HEALTHY":
        overall_status = "ERROR"
        health_reason = "UI Shell service/port/http health failed"
        recommended_action = "Проверить systemctl status marketcore-ui-shell.service и journalctl."
    else:
        overall_status = "HEALTHY"
        health_reason = "KG API and UI Shell are active; /, /risk and /settings are reachable."
        recommended_action = "Открыть MarketCore UI Shell на 8080."

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1 ===")

            cur.execute("""
                INSERT INTO marketcore_ui.marketcore_ui_systemd_8080_health_v1 (
                    id,
                    kg_api_unit,
                    ui_shell_unit,
                    kg_api_active_state,
                    kg_api_sub_state,
                    kg_api_result,
                    kg_api_main_status,
                    kg_api_healthy,
                    ui_shell_active_state,
                    ui_shell_sub_state,
                    ui_shell_result,
                    ui_shell_main_status,
                    ui_shell_healthy,
                    kg_api_port,
                    ui_shell_port,
                    kg_api_http_ok,
                    ui_home_http_ok,
                    ui_risk_http_ok,
                    ui_settings_http_ok,
                    kg_api_health_status,
                    ui_shell_health_status,
                    overall_status,
                    open_url,
                    risk_url,
                    settings_url,
                    health_reason,
                    recommended_action,
                    runtime_changed,
                    execution_changed,
                    orders_changed,
                    fills_changed,
                    micro_live_allowed,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,
                    0,0,0,0,0,
                    now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    kg_api_unit=EXCLUDED.kg_api_unit,
                    ui_shell_unit=EXCLUDED.ui_shell_unit,
                    kg_api_active_state=EXCLUDED.kg_api_active_state,
                    kg_api_sub_state=EXCLUDED.kg_api_sub_state,
                    kg_api_result=EXCLUDED.kg_api_result,
                    kg_api_main_status=EXCLUDED.kg_api_main_status,
                    kg_api_healthy=EXCLUDED.kg_api_healthy,
                    ui_shell_active_state=EXCLUDED.ui_shell_active_state,
                    ui_shell_sub_state=EXCLUDED.ui_shell_sub_state,
                    ui_shell_result=EXCLUDED.ui_shell_result,
                    ui_shell_main_status=EXCLUDED.ui_shell_main_status,
                    ui_shell_healthy=EXCLUDED.ui_shell_healthy,
                    kg_api_port=EXCLUDED.kg_api_port,
                    ui_shell_port=EXCLUDED.ui_shell_port,
                    kg_api_http_ok=EXCLUDED.kg_api_http_ok,
                    ui_home_http_ok=EXCLUDED.ui_home_http_ok,
                    ui_risk_http_ok=EXCLUDED.ui_risk_http_ok,
                    ui_settings_http_ok=EXCLUDED.ui_settings_http_ok,
                    kg_api_health_status=EXCLUDED.kg_api_health_status,
                    ui_shell_health_status=EXCLUDED.ui_shell_health_status,
                    overall_status=EXCLUDED.overall_status,
                    open_url=EXCLUDED.open_url,
                    risk_url=EXCLUDED.risk_url,
                    settings_url=EXCLUDED.settings_url,
                    health_reason=EXCLUDED.health_reason,
                    recommended_action=EXCLUDED.recommended_action,
                    runtime_changed=EXCLUDED.runtime_changed,
                    execution_changed=EXCLUDED.execution_changed,
                    orders_changed=EXCLUDED.orders_changed,
                    fills_changed=EXCLUDED.fills_changed,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                KG_API_UNIT,
                UI_SHELL_UNIT,
                kg_api_active_state,
                kg_api_sub_state,
                kg_api_result,
                kg_api_main_status,
                kg_api_healthy,
                ui_shell_active_state,
                ui_shell_sub_state,
                ui_shell_result,
                ui_shell_main_status,
                ui_shell_healthy,
                KG_API_PORT,
                UI_SHELL_PORT,
                kg_api_http_ok,
                ui_home_http_ok,
                ui_risk_http_ok,
                ui_settings_http_ok,
                kg_api_health_status,
                ui_shell_health_status,
                overall_status,
                open_url,
                risk_url,
                settings_url,
                health_reason,
                recommended_action,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"kg_api_active_state={kg_api_active_state}")
    print(f"kg_api_healthy={int(kg_api_healthy)}")
    print(f"kg_api_http_ok={int(kg_api_http_ok)}")
    print(f"ui_shell_active_state={ui_shell_active_state}")
    print(f"ui_shell_healthy={int(ui_shell_healthy)}")
    print(f"ui_home_http_ok={int(ui_home_http_ok)}")
    print(f"ui_risk_http_ok={int(ui_risk_http_ok)}")
    print(f"ui_settings_http_ok={int(ui_settings_http_ok)}")
    print(f"overall_status={overall_status}")
    print(f"open_url={open_url}")
    print(f"risk_url={risk_url}")
    print(f"settings_url={settings_url}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_READY")


if __name__ == "__main__":
    main()
