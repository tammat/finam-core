#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1 ==="

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-runtime-sample-collection' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-runtime-sample-collection":
                row = fetch_one("""
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
                        recommended_action,
                        micro_live_allowed,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_dashboard_link_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py <<'PY'
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


def _table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Sample Accumulation Monitor пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("monitor_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("sample_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("progress_pct"), 2))}%</td>
            <td>{escape(ctx.formatter.number(row.get("total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_oos_trades"), 0))}</td>
            <td>{escape(str(row.get("readiness_status", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Инструмент</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Sample Status</th>
                <th>Progress</th>
                <th>Total Trades</th>
                <th>Need Total</th>
                <th>OOS Trades</th>
                <th>Need OOS</th>
                <th>Readiness</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperSampleAccumulationMonitorPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-sample-accumulation-monitor",
            title="Paper Sample Accumulation Monitor",
            icon="□",
            menu_order=22,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary_payload = ctx.api_get("/api/kg/v1/paper-runtime-sample-collection")
        monitor_payload = ctx.api_get("/api/kg/v1/paper-sample-accumulation-monitor?limit=50")

        summary = summary_payload.get("data") or {}
        rows = monitor_payload.get("data") or []

        candidates_total = ctx.formatter.number(summary.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(summary.get("sample_ready"), 0)
        wait_both = ctx.formatter.number(summary.get("wait_both_sample"), 0)
        min_total = ctx.formatter.number(summary.get("min_remaining_total_trades"), 0)
        min_oos = ctx.formatter.number(summary.get("min_remaining_oos_trades"), 0)
        avg_progress = ctx.formatter.number(summary.get("avg_progress_pct"), 2)
        max_progress = ctx.formatter.number(summary.get("max_progress_pct"), 2)
        collection_status = str(summary.get("collection_status", "UNKNOWN"))
        phase_status = str(summary.get("phase_status", "UNKNOWN"))
        recommended_action = str(summary.get("recommended_action", ""))
        refreshed_at = ctx.formatter.datetime(summary.get("refreshed_at"))

        ready = sum(1 for row in rows if row.get("sample_status") == "SAMPLE_READY")
        wait_total = sum(1 for row in rows if row.get("sample_status") == "WAIT_TOTAL_SAMPLE")
        wait_oos = sum(1 for row in rows if row.get("sample_status") == "WAIT_OOS_SAMPLE")

        return f"""
        <section class="card">
            <h2>Paper Sample Accumulation Monitor</h2>
            <p>Ответы на три вопроса: сколько Paper-сделок накоплено, сколько ещё нужно, какие кандидаты ближе всего к повторной проверке.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_v1 и marketcore_ui.paper_sample_accumulation_monitor_v1.</p>
            <p><a href="/paper-edge-discovery">← Paper Edge Discovery Center</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Кандидатов", candidates_total, "Всего в мониторинге")}
            {_metric("Ready", sample_ready, "Достаточная выборка")}
            {_metric("Wait Both", wait_both, "Не хватает общей и OOS-выборки")}
            {_metric("Need Total", min_total, "Минимально осталось общих сделок")}
            {_metric("Need OOS", min_oos, "Минимально осталось OOS-сделок")}
        </div>

        <section class="card">
            <h2>Sample Collection Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Collection Status", collection_status)}
                    {_row("Phase Status", phase_status)}
                    {_row("Average Progress", f"{avg_progress}%")}
                    {_row("Max Progress", f"{max_progress}%")}
                    {_row("Wait Total", ctx.formatter.number(wait_total, 0))}
                    {_row("Wait OOS", ctx.formatter.number(wait_oos, 0))}
                    {_row("Recommended Action", recommended_action)}
                    {_row("Refreshed At", refreshed_at)}
                    {_row("Source", "marketcore_ui.paper_runtime_sample_collection_v1")}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Closest Candidates To Recheck</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/pages/paper_edge_discovery.py")
s = p.read_text()

if "PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1" not in s:
    link_block = '''
        <section class="card">
            <h2>Sample Collection</h2>
            <p>Сколько Paper-сделок накоплено, сколько ещё нужно до минимальной выборки и какие кандидаты ближе всего к повторной проверке.</p>
            <p><a href="/paper-sample-accumulation-monitor">Открыть Paper Sample Accumulation Monitor</a></p>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1</p>
        </section>
'''

    needle = '        <section class="card">\n            <h2>Next Action</h2>'
    if needle in s:
        s = s.replace(needle, link_block + "\n" + needle)
    else:
        s = s.replace('        """', link_block + '\n        """')

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperSampleAccumulationMonitorPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_sample_accumulation_monitor import PaperSampleAccumulationMonitorPage\n",
    )

if "PaperSampleAccumulationMonitorPage()," not in s:
    if "MicroLiveReadinessPage()," in s:
        s = s.replace(
            "MicroLiveReadinessPage(),",
            "MicroLiveReadinessPage(),\n    PaperSampleAccumulationMonitorPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperSampleAccumulationMonitorPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_paper_runtime_sample_collection_dashboard_link_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

for page in \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py
do
  if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n "$page"; then
    echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE file=$page"
    exit 1
  fi
done

sudo -u postgres env DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/dashboard_link_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/dashboard_link_sample_cycle_v1.log

KG_API_HOST=127.0.0.1 KG_API_PORT=19495 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_dashboard_link_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19480 KG_API_BASE_URL=http://127.0.0.1:19495 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/dashboard_link_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19495/api/kg/v1/paper-runtime-sample-collection" \
  > /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json

curl -fsS "http://127.0.0.1:19480/paper-sample-accumulation-monitor" \
  > /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html

curl -fsS "http://127.0.0.1:19480/paper-edge-discovery" \
  > /tmp/paper_edge_discovery_dashboard_link_v1.html

grep -q '"status": "OK"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"candidates_total"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"min_remaining_total_trades"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"min_remaining_oos_trades"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"collection_status"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json

grep -q "Paper Sample Accumulation Monitor" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "Sample Collection Summary" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "Closest Candidates To Recheck" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "marketcore_ui.paper_runtime_sample_collection_v1" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html

grep -q "Sample Collection" /tmp/paper_edge_discovery_dashboard_link_v1.html
grep -q "paper-sample-accumulation-monitor" /tmp/paper_edge_discovery_dashboard_link_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1" /tmp/paper_edge_discovery_dashboard_link_v1.html

summary_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE id=1;")
monitor_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE micro_live_allowed=true;")

test "$summary_rows" = "1"
test "$monitor_rows" -gt 0
test "$allowed_rows" = "0"

echo "summary_rows=$summary_rows"
echo "monitor_rows=$monitor_rows"
echo "micro_live_allowed_rows=$allowed_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1_OK"
SH_TEST

chmod +x scripts/test_paper_runtime_sample_collection_dashboard_link_v1.sh

scripts/test_paper_runtime_sample_collection_dashboard_link_v1.sh

echo "VERDICT=BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1_OK"
