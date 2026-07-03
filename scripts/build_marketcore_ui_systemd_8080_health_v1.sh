#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/026_marketcore_ui_systemd_8080_health_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.marketcore_ui_systemd_8080_health_v1 (
    id SMALLINT PRIMARY KEY,

    kg_api_unit TEXT NOT NULL DEFAULT 'marketcore-kg-api.service',
    ui_shell_unit TEXT NOT NULL DEFAULT 'marketcore-ui-shell.service',

    kg_api_active_state TEXT NOT NULL DEFAULT 'unknown',
    kg_api_sub_state TEXT NOT NULL DEFAULT 'unknown',
    kg_api_result TEXT NOT NULL DEFAULT 'unknown',
    kg_api_main_status TEXT NOT NULL DEFAULT '',
    kg_api_healthy BOOLEAN NOT NULL DEFAULT false,

    ui_shell_active_state TEXT NOT NULL DEFAULT 'unknown',
    ui_shell_sub_state TEXT NOT NULL DEFAULT 'unknown',
    ui_shell_result TEXT NOT NULL DEFAULT 'unknown',
    ui_shell_main_status TEXT NOT NULL DEFAULT '',
    ui_shell_healthy BOOLEAN NOT NULL DEFAULT false,

    kg_api_port INTEGER NOT NULL DEFAULT 8095,
    ui_shell_port INTEGER NOT NULL DEFAULT 8080,

    kg_api_http_ok BOOLEAN NOT NULL DEFAULT false,
    ui_home_http_ok BOOLEAN NOT NULL DEFAULT false,
    ui_risk_http_ok BOOLEAN NOT NULL DEFAULT false,
    ui_settings_http_ok BOOLEAN NOT NULL DEFAULT false,

    kg_api_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ui_shell_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    overall_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    open_url TEXT NOT NULL DEFAULT '',
    risk_url TEXT NOT NULL DEFAULT '',
    settings_url TEXT NOT NULL DEFAULT '',

    health_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    runtime_changed INTEGER NOT NULL DEFAULT 0,
    execution_changed INTEGER NOT NULL DEFAULT 0,
    orders_changed INTEGER NOT NULL DEFAULT 0,
    fills_changed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.marketcore_ui_systemd_8080_health_v1 TO alex;

COMMIT;

SELECT 'MARKETCORE_UI_SYSTEMD_8080_HEALTH_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_marketcore_ui_systemd_8080_health_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/026_marketcore_ui_systemd_8080_health_v1.sql
SH_APPLY

chmod +x scripts/apply_marketcore_ui_systemd_8080_health_v1.sh

cat > src/scripts/build_marketcore_ui_systemd_8080_health_v1.py <<'PY'
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
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/marketcore-ui-systemd-health' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/marketcore-ui-systemd-health":
                row = fetch_one("""
                    SELECT
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
                        source_version
                    FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.marketcore_ui_systemd_8080_health_v1",
                    "ui_direct_sql": 0,
                    "logic": "marketcore_ui_systemd_8080_health_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/marketcore_ui_systemd_health.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _metric(title: str, value: str, note: str = "") -> str:
    return f"""
    <section class="card">
        <h2>{escape(title)}</h2>
        <p style="font-size:28px;font-weight:700;margin:8px 0;">{escape(value)}</p>
        <p>{escape(note)}</p>
    </section>
    """


def _row(label: str, value: str) -> str:
    return f"""
    <tr>
        <td>{escape(label)}</td>
        <td>{escape(value)}</td>
    </tr>
    """


class MarketcoreUiSystemdHealthPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/marketcore-ui-systemd-health",
            title="MarketCore UI Systemd Health",
            icon="⚙",
            menu_order=121,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/marketcore-ui-systemd-health")
        data = payload.get("data") or {}

        overall = str(data.get("overall_status", "UNKNOWN"))
        kg = str(data.get("kg_api_health_status", "UNKNOWN"))
        ui = str(data.get("ui_shell_health_status", "UNKNOWN"))

        return f"""
        <section class="card">
            <h2>MarketCore UI Systemd Health</h2>
            <p>Контроль KG API на 8095 и MarketCore UI Shell на 8080.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.marketcore_ui_systemd_8080_health_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Overall", overall)}
            {_metric("KG API", kg, str(data.get("kg_api_active_state", "")))}
            {_metric("UI Shell", ui, str(data.get("ui_shell_active_state", "")))}
            {_metric("8080", str(data.get("ui_home_http_ok", "")), str(data.get("open_url", "")))}
            {_metric("Safety", "OK" if data.get("micro_live_allowed") in {False, 0, None} else "ERROR", "micro_live_allowed=0")}
        </div>

        <section class="card">
            <h2>Systemd Details</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("KG API Unit", str(data.get("kg_api_unit", "")))}
                    {_row("KG API Active", str(data.get("kg_api_active_state", "")))}
                    {_row("KG API Result", str(data.get("kg_api_result", "")))}
                    {_row("KG API HTTP OK", str(data.get("kg_api_http_ok", "")))}
                    {_row("UI Shell Unit", str(data.get("ui_shell_unit", "")))}
                    {_row("UI Shell Active", str(data.get("ui_shell_active_state", "")))}
                    {_row("UI Shell Result", str(data.get("ui_shell_result", "")))}
                    {_row("Home HTTP OK", str(data.get("ui_home_http_ok", "")))}
                    {_row("Risk HTTP OK", str(data.get("ui_risk_http_ok", "")))}
                    {_row("Settings HTTP OK", str(data.get("ui_settings_http_ok", "")))}
                    {_row("Open URL", str(data.get("open_url", "")))}
                    {_row("Risk URL", str(data.get("risk_url", "")))}
                    {_row("Settings URL", str(data.get("settings_url", "")))}
                    {_row("Health Reason", str(data.get("health_reason", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "MarketcoreUiSystemdHealthPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.marketcore_ui_systemd_health import MarketcoreUiSystemdHealthPage\n",
    )

if "MarketcoreUiSystemdHealthPage()," not in s:
    if "SettingsPage()," in s:
        s = s.replace(
            "SettingsPage(),",
            "SettingsPage(),\n    MarketcoreUiSystemdHealthPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    MarketcoreUiSystemdHealthPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_marketcore_ui_systemd_8080_health_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1 ==="

scripts/apply_marketcore_ui_systemd_8080_health_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_marketcore_ui_systemd_8080_health_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/marketcore_ui_systemd_health.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/marketcore_ui_systemd_health.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

sleep 2

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_marketcore_ui_systemd_8080_health_v1.py \
  | tee /tmp/marketcore_ui_systemd_8080_health_builder_v1.txt

grep -q "VERDICT=MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_READY" \
  /tmp/marketcore_ui_systemd_8080_health_builder_v1.txt

curl -fsS "http://127.0.0.1:8095/api/kg/v1/marketcore-ui-systemd-health" \
  > /tmp/marketcore_ui_systemd_8080_health_api_v1.json

curl -fsS "http://127.0.0.1:8080/marketcore-ui-systemd-health" \
  > /tmp/marketcore_ui_systemd_8080_health_page_v1.html

grep -q '"status": "OK"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"overall_status"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"kg_api_health_status"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"ui_shell_health_status"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"open_url"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json

grep -q "MarketCore UI Systemd Health" /tmp/marketcore_ui_systemd_8080_health_page_v1.html
grep -q "Systemd Details" /tmp/marketcore_ui_systemd_8080_health_page_v1.html
grep -q "MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1" /tmp/marketcore_ui_systemd_8080_health_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_ui_systemd_8080_health_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1 WHERE micro_live_allowed<>0;")
overall=$(psql -At -d finam_core -c "SELECT overall_status FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1 WHERE id=1;")

test "$rows" = "1"
test "$allowed" = "0"
test "$overall" = "HEALTHY"

psql -d finam_core -c "
SELECT
    overall_status,
    kg_api_health_status,
    ui_shell_health_status,
    kg_api_http_ok,
    ui_home_http_ok,
    ui_risk_http_ok,
    ui_settings_http_ok,
    open_url,
    risk_url,
    settings_url
FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1
WHERE id=1;
"

echo "marketcore_ui_health_rows=$rows"
echo "overall_status=$overall"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_systemd_8080_health_v1.sh

scripts/test_marketcore_ui_systemd_8080_health_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_OK"
