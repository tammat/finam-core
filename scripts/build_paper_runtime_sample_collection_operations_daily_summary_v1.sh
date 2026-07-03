#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/025_paper_runtime_sample_collection_operations_daily_summary_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 (
    id SMALLINT PRIMARY KEY,
    summary_date DATE NOT NULL DEFAULT CURRENT_DATE,

    phase_result_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    engineering_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operational_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_close_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    sample_collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    sample_phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operations_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    operations_rows INTEGER NOT NULL DEFAULT 0,
    operations_high_rows INTEGER NOT NULL DEFAULT 0,
    operations_near_ready_rows INTEGER NOT NULL DEFAULT 0,
    operations_collecting_rows INTEGER NOT NULL DEFAULT 0,

    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    wait_both_sample INTEGER NOT NULL DEFAULT 0,

    avg_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    min_remaining_total_trades INTEGER,
    min_remaining_oos_trades INTEGER,

    micro_live_allowed_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    daily_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    conclusion TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_runtime_sample_collection_operations_daily_summary_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/025_paper_runtime_sample_collection_operations_daily_summary_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_runtime_sample_collection_operations_daily_summary_v1.sh

cat > src/scripts/build_paper_runtime_sample_collection_operations_daily_summary_v1.py <<'PY'
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
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-sample-operations-daily-summary' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-sample-operations-daily-summary":
                row = fetch_one("""
                    SELECT
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
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_operations_daily_summary_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/risk.py <<'PY'
from __future__ import annotations

from marketcore.presentation.page import Page


class RiskPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/risk",
            title="Риски",
            icon="⚠",
            menu_order=70,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Риски</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
PY

cat > src/marketcore/presentation/pages/settings.py <<'PY'
from __future__ import annotations

from marketcore.presentation.page import Page


class SettingsPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/settings",
            title="Настройки",
            icon="⚙",
            menu_order=120,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Настройки</h2>
            <p>Раздел подключён к MarketCore UI Shell. Здесь будут настройки локали, валюты, таймзоны, темы и API.</p>
        </section>
        """
PY

cat > src/marketcore/presentation/pages/paper_runtime_sample_collection_daily_summary.py <<'PY'
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


class PaperRuntimeSampleCollectionDailySummaryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-runtime-sample-collection-daily-summary",
            title="Paper Runtime Sample Collection Daily Summary",
            icon="□",
            menu_order=28,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-sample-operations-daily-summary")
        data = payload.get("data") or {}

        daily_status = str(data.get("daily_status", "UNKNOWN"))
        operational_status = str(data.get("operational_status", "UNKNOWN"))
        operations_health = str(data.get("operations_health_status", "UNKNOWN"))

        return f"""
        <section class="card">
            <h2>Paper Runtime Sample Collection Daily Summary</h2>
            <p>Ежедневная сводка по операционному накоплению Paper/OOS выборки.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Daily Status", daily_status)}
            {_metric("Operational", operational_status)}
            {_metric("Operations Health", operations_health)}
            {_metric("Candidates", ctx.formatter.number(data.get("candidates_total"), 0))}
            {_metric("Micro Live Allowed", str(data.get("micro_live_allowed", False)))}
        </div>

        <section class="card">
            <h2>Daily Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Summary Date", str(data.get("summary_date", "")))}
                    {_row("Phase Result", str(data.get("phase_result_status", "")))}
                    {_row("Engineering", str(data.get("engineering_status", "")))}
                    {_row("Operational", operational_status)}
                    {_row("Phase Close", str(data.get("phase_close_status", "")))}
                    {_row("Timer Health", str(data.get("timer_health_status", "")))}
                    {_row("Operations Health", operations_health)}
                    {_row("Operations Rows", ctx.formatter.number(data.get("operations_rows"), 0))}
                    {_row("Operations High Rows", ctx.formatter.number(data.get("operations_high_rows"), 0))}
                    {_row("Operations Near Ready Rows", ctx.formatter.number(data.get("operations_near_ready_rows"), 0))}
                    {_row("Operations Collecting Rows", ctx.formatter.number(data.get("operations_collecting_rows"), 0))}
                    {_row("Candidates Total", ctx.formatter.number(data.get("candidates_total"), 0))}
                    {_row("Sample Ready", ctx.formatter.number(data.get("sample_ready"), 0))}
                    {_row("Wait Both Sample", ctx.formatter.number(data.get("wait_both_sample"), 0))}
                    {_row("Average Progress", ctx.formatter.number(data.get("avg_progress_pct"), 2) + "%")}
                    {_row("Max Progress", ctx.formatter.number(data.get("max_progress_pct"), 2) + "%")}
                    {_row("Min Remaining Total Trades", ctx.formatter.number(data.get("min_remaining_total_trades"), 0))}
                    {_row("Min Remaining OOS Trades", ctx.formatter.number(data.get("min_remaining_oos_trades"), 0))}
                    {_row("Micro Live Allowed Rows", ctx.formatter.number(data.get("micro_live_allowed_rows"), 0))}
                    {_row("Conclusion", str(data.get("conclusion", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Навигация</h2>
            <p><a href="/risk">Риски</a></p>
            <p><a href="/settings">Настройки</a></p>
            <p><a href="/paper-runtime-sample-collection-operations">Operations Queue</a></p>
            <p><a href="/paper-sample-operations-timer-health">Operations Timer Health</a></p>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

imports = {
    "RiskPage": "from marketcore.presentation.pages.risk import RiskPage\n",
    "SettingsPage": "from marketcore.presentation.pages.settings import SettingsPage\n",
    "PaperRuntimeSampleCollectionDailySummaryPage": "from marketcore.presentation.pages.paper_runtime_sample_collection_daily_summary import PaperRuntimeSampleCollectionDailySummaryPage\n",
}

for class_name, import_line in imports.items():
    if class_name not in s:
        s = s.replace(
            "from marketcore.presentation.pages.home import HomePage\n",
            "from marketcore.presentation.pages.home import HomePage\n" + import_line,
        )

if "PaperRuntimeSampleCollectionDailySummaryPage()," not in s:
    if "PaperSampleOperationsTimerHealthPage()," in s:
        s = s.replace(
            "PaperSampleOperationsTimerHealthPage(),",
            "PaperSampleOperationsTimerHealthPage(),\n    PaperRuntimeSampleCollectionDailySummaryPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperRuntimeSampleCollectionDailySummaryPage(),",
        )

if "RiskPage()," not in s:
    s = s.replace(
        "HomePage(),",
        "HomePage(),\n    RiskPage(),",
    )

if "SettingsPage()," not in s:
    s = s.replace(
        "HomePage(),",
        "HomePage(),\n    SettingsPage(),",
    )

p.write_text(s)
PY

cat > scripts/test_paper_runtime_sample_collection_operations_daily_summary_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1 ==="

scripts/apply_paper_runtime_sample_collection_operations_daily_summary_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_operations_daily_summary_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_runtime_sample_collection_daily_summary.py \
  src/marketcore/presentation/pages/risk.py \
  src/marketcore/presentation/pages/settings.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

for page in \
  src/marketcore/presentation/pages/paper_runtime_sample_collection_daily_summary.py \
  src/marketcore/presentation/pages/risk.py \
  src/marketcore/presentation/pages/settings.py
do
  if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n "$page"; then
    echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE file=$page"
    exit 1
  fi
done

sudo -u postgres env DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_operations_cycle_v1.py \
  > /tmp/daily_summary_operations_cycle_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_CYCLE_V1_READY" \
  /tmp/daily_summary_operations_cycle_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_operations_timer_health_v1.py \
  > /tmp/daily_summary_operations_health_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1_READY" \
  /tmp/daily_summary_operations_health_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_operations_daily_summary_v1.py \
  | tee /tmp/daily_summary_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_READY" \
  /tmp/daily_summary_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=20095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_daily_summary_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20080 KG_API_BASE_URL=http://127.0.0.1:20095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/daily_summary_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:20095/api/kg/v1/paper-sample-operations-daily-summary" \
  > /tmp/daily_summary_api_v1.json

curl -fsS "http://127.0.0.1:20080/paper-runtime-sample-collection-daily-summary" \
  > /tmp/daily_summary_page_v1.html

curl -fsS "http://127.0.0.1:20080/risk" \
  > /tmp/risk_page_v1.html

curl -fsS "http://127.0.0.1:20080/settings" \
  > /tmp/settings_page_v1.html

grep -q '"status": "OK"' /tmp/daily_summary_api_v1.json
grep -q '"daily_status"' /tmp/daily_summary_api_v1.json
grep -q '"operations_health_status"' /tmp/daily_summary_api_v1.json
grep -q '"micro_live_allowed"' /tmp/daily_summary_api_v1.json

grep -q "Paper Runtime Sample Collection Daily Summary" /tmp/daily_summary_page_v1.html
grep -q "Daily Summary" /tmp/daily_summary_page_v1.html
grep -q "Риски" /tmp/daily_summary_page_v1.html
grep -q "Настройки" /tmp/daily_summary_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1" /tmp/daily_summary_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/daily_summary_page_v1.html

grep -q "Риски" /tmp/risk_page_v1.html
grep -q "Настройки" /tmp/settings_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 WHERE micro_live_allowed=true;")

test "$rows" = "1"
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    daily_status,
    phase_result_status,
    engineering_status,
    operational_status,
    operations_health_status,
    operations_rows,
    candidates_total,
    sample_ready,
    wait_both_sample,
    micro_live_allowed,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1
WHERE id=1;
"

echo "daily_summary_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "risk_page_ready=READY"
echo "settings_page_ready=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_OK"
SH_TEST

chmod +x scripts/test_paper_runtime_sample_collection_operations_daily_summary_v1.sh

scripts/test_paper_runtime_sample_collection_operations_daily_summary_v1.sh

echo "VERDICT=BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_OK"
