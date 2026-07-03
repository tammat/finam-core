#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/020_paper_runtime_sample_collection_timer_health_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_timer_health_v1 (
    id SMALLINT PRIMARY KEY,

    timer_unit TEXT NOT NULL DEFAULT 'finam-paper-sample-collection.timer',
    service_unit TEXT NOT NULL DEFAULT 'finam-paper-sample-collection.service',

    timer_active_state TEXT NOT NULL DEFAULT 'unknown',
    timer_sub_state TEXT NOT NULL DEFAULT 'unknown',
    timer_unit_file_state TEXT NOT NULL DEFAULT 'unknown',
    timer_next_elapse TEXT NOT NULL DEFAULT '',
    timer_last_trigger TEXT NOT NULL DEFAULT '',
    timer_healthy BOOLEAN NOT NULL DEFAULT false,

    service_active_state TEXT NOT NULL DEFAULT 'unknown',
    service_sub_state TEXT NOT NULL DEFAULT 'unknown',
    service_result TEXT NOT NULL DEFAULT 'unknown',
    service_exec_main_status TEXT NOT NULL DEFAULT '',
    service_last_exit TEXT NOT NULL DEFAULT '',
    service_healthy BOOLEAN NOT NULL DEFAULT false,

    sample_summary_exists BOOLEAN NOT NULL DEFAULT false,
    sample_summary_refreshed_at TIMESTAMPTZ,
    sample_summary_age_sec INTEGER,
    sample_summary_stale BOOLEAN NOT NULL DEFAULT true,

    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_timer_health_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_runtime_sample_collection_timer_health_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/020_paper_runtime_sample_collection_timer_health_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_runtime_sample_collection_timer_health_v1.sh

cat > src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py <<'PY'
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
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-sample-collection-timer-health' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-sample-collection-timer-health":
                row = fetch_one("""
                    SELECT
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
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_timer_health_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_timer_health_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_sample_collection_timer_health.py <<'PY'
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


class PaperSampleCollectionTimerHealthPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-sample-collection-timer-health",
            title="Paper Sample Collection Timer Health",
            icon="⚙",
            menu_order=23,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-sample-collection-timer-health")
        data = payload.get("data") or {}

        health = str(data.get("timer_health_status", "UNKNOWN"))
        timer_active = str(data.get("timer_active_state", "unknown"))
        service_result = str(data.get("service_result", "unknown"))
        age_sec = ctx.formatter.number(data.get("sample_summary_age_sec"), 0)
        candidates_total = ctx.formatter.number(data.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(data.get("sample_ready"), 0)

        return f"""
        <section class="card">
            <h2>Paper Sample Collection Timer Health</h2>
            <p>Контроль systemd timer/service и свежести sample collection summary.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_timer_health_v1.</p>
            <p><a href="/paper-sample-accumulation-monitor">← Paper Sample Accumulation Monitor</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Health", health, str(data.get("health_reason", "")))}
            {_metric("Timer", timer_active, str(data.get("timer_unit_file_state", "")))}
            {_metric("Service", service_result, str(data.get("service_active_state", "")))}
            {_metric("Age Sec", age_sec, "Возраст summary")}
            {_metric("Candidates", candidates_total, f"sample_ready={sample_ready}")}
        </div>

        <section class="card">
            <h2>Timer Details</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Timer Unit", str(data.get("timer_unit", "")))}
                    {_row("Timer Active State", str(data.get("timer_active_state", "")))}
                    {_row("Timer Sub State", str(data.get("timer_sub_state", "")))}
                    {_row("Timer Unit File State", str(data.get("timer_unit_file_state", "")))}
                    {_row("Next Elapse", str(data.get("timer_next_elapse", "")))}
                    {_row("Last Trigger", str(data.get("timer_last_trigger", "")))}
                    {_row("Timer Healthy", str(data.get("timer_healthy", "")))}
                    {_row("Service Unit", str(data.get("service_unit", "")))}
                    {_row("Service Active State", str(data.get("service_active_state", "")))}
                    {_row("Service Result", str(data.get("service_result", "")))}
                    {_row("Service Healthy", str(data.get("service_healthy", "")))}
                    {_row("Summary Exists", str(data.get("sample_summary_exists", "")))}
                    {_row("Summary Stale", str(data.get("sample_summary_stale", "")))}
                    {_row("Collection Status", str(data.get("collection_status", "")))}
                    {_row("Phase Status", str(data.get("phase_status", "")))}
                    {_row("Micro Live Allowed", str(data.get("micro_live_allowed", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperSampleCollectionTimerHealthPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_sample_collection_timer_health import PaperSampleCollectionTimerHealthPage\n",
    )

if "PaperSampleCollectionTimerHealthPage()," not in s:
    if "PaperSampleAccumulationMonitorPage()," in s:
        s = s.replace(
            "PaperSampleAccumulationMonitorPage(),",
            "PaperSampleAccumulationMonitorPage(),\n    PaperSampleCollectionTimerHealthPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperSampleCollectionTimerHealthPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_paper_runtime_sample_collection_timer_health_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1 ==="

scripts/apply_paper_runtime_sample_collection_timer_health_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_sample_collection_timer_health.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_sample_collection_timer_health.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/timer_health_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/timer_health_sample_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  | tee /tmp/paper_runtime_sample_collection_timer_health_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY" \
  /tmp/paper_runtime_sample_collection_timer_health_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19595 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_timer_health_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19580 KG_API_BASE_URL=http://127.0.0.1:19595 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/timer_health_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19595/api/kg/v1/paper-sample-collection-timer-health" \
  > /tmp/paper_sample_collection_timer_health_api_v1.json

curl -fsS "http://127.0.0.1:19580/paper-sample-collection-timer-health" \
  > /tmp/paper_sample_collection_timer_health_page_v1.html

grep -q '"status": "OK"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"timer_health_status"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"timer_active_state"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"service_result"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"sample_summary_age_sec"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"micro_live_allowed"' /tmp/paper_sample_collection_timer_health_api_v1.json

grep -q "Paper Sample Collection Timer Health" /tmp/paper_sample_collection_timer_health_page_v1.html
grep -q "Timer Details" /tmp/paper_sample_collection_timer_health_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1" /tmp/paper_sample_collection_timer_health_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_sample_collection_timer_health_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1 WHERE micro_live_allowed=true;")

test "$rows" = "1"
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    timer_health_status,
    timer_active_state,
    timer_unit_file_state,
    service_result,
    sample_summary_age_sec,
    sample_summary_stale,
    candidates_total,
    sample_ready,
    collection_status,
    phase_status,
    micro_live_allowed,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
WHERE id=1;
"

echo "timer_health_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_OK"
SH_TEST

chmod +x scripts/test_paper_runtime_sample_collection_timer_health_v1.sh

scripts/test_paper_runtime_sample_collection_timer_health_v1.sh

echo "VERDICT=BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_OK"
