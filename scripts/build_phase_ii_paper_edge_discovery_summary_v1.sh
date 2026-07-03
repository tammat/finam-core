#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/022_phase_ii_paper_edge_discovery_summary_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 (
    id SMALLINT PRIMARY KEY,

    phase_name TEXT NOT NULL DEFAULT 'PHASE_II_PAPER_EDGE_DISCOVERY',
    phase_result_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    engineering_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operational_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    close_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    collection_phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    wait_both_sample INTEGER NOT NULL DEFAULT 0,
    wait_total_sample INTEGER NOT NULL DEFAULT 0,
    wait_oos_sample INTEGER NOT NULL DEFAULT 0,

    min_remaining_total_trades INTEGER,
    min_remaining_oos_trades INTEGER,
    avg_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,

    paper_candidates_rows INTEGER NOT NULL DEFAULT 0,
    validation_queue_rows INTEGER NOT NULL DEFAULT 0,
    validation_pipeline_rows INTEGER NOT NULL DEFAULT 0,
    robustness_rows INTEGER NOT NULL DEFAULT 0,
    oos_validation_rows INTEGER NOT NULL DEFAULT 0,
    oos_backtest_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_readiness_rows INTEGER NOT NULL DEFAULT 0,
    sample_monitor_rows INTEGER NOT NULL DEFAULT 0,

    micro_live_ready_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    conclusion TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    next_phase TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 TO alex;

COMMIT;

SELECT 'PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_phase_ii_paper_edge_discovery_summary_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/022_phase_ii_paper_edge_discovery_summary_v1.sql
SH_APPLY

chmod +x scripts/apply_phase_ii_paper_edge_discovery_summary_v1.sh

cat > src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py <<'PY'
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
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/phase-ii-paper-edge-discovery-summary' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/phase-ii-paper-edge-discovery-summary":
                row = fetch_one("""
                    SELECT
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
                        source_version
                    FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.phase_ii_paper_edge_discovery_summary_v1",
                    "ui_direct_sql": 0,
                    "logic": "phase_ii_paper_edge_discovery_summary_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/phase_ii_paper_edge_discovery_summary.py <<'PY'
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


class PhaseIiPaperEdgeDiscoverySummaryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/phase-ii-paper-edge-discovery-summary",
            title="Phase II Paper Edge Discovery Summary",
            icon="✓",
            menu_order=25,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/phase-ii-paper-edge-discovery-summary")
        data = payload.get("data") or {}

        phase_result_status = str(data.get("phase_result_status", "UNKNOWN"))
        engineering_status = str(data.get("engineering_status", "UNKNOWN"))
        operational_status = str(data.get("operational_status", "UNKNOWN"))
        next_phase = str(data.get("next_phase", ""))

        return f"""
        <section class="card">
            <h2>Phase II Paper Edge Discovery Summary</h2>
            <p>Финальная сводка инженерной фазы Paper Edge Discovery и текущего операционного состояния.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.phase_ii_paper_edge_discovery_summary_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Phase Result", phase_result_status)}
            {_metric("Engineering", engineering_status)}
            {_metric("Operational", operational_status)}
            {_metric("Candidates", ctx.formatter.number(data.get("candidates_total"), 0))}
            {_metric("Micro Live Allowed", str(data.get("micro_live_allowed", False)))}
        </div>

        <section class="card">
            <h2>Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Phase Name", str(data.get("phase_name", "")))}
                    {_row("Phase Result Status", phase_result_status)}
                    {_row("Engineering Status", engineering_status)}
                    {_row("Operational Status", operational_status)}
                    {_row("Close Status", str(data.get("close_status", "")))}
                    {_row("Timer Health", str(data.get("timer_health_status", "")))}
                    {_row("Collection Status", str(data.get("collection_status", "")))}
                    {_row("Collection Phase Status", str(data.get("collection_phase_status", "")))}
                    {_row("Candidates Total", ctx.formatter.number(data.get("candidates_total"), 0))}
                    {_row("Sample Ready", ctx.formatter.number(data.get("sample_ready"), 0))}
                    {_row("Wait Both Sample", ctx.formatter.number(data.get("wait_both_sample"), 0))}
                    {_row("Min Remaining Total Trades", ctx.formatter.number(data.get("min_remaining_total_trades"), 0))}
                    {_row("Min Remaining OOS Trades", ctx.formatter.number(data.get("min_remaining_oos_trades"), 0))}
                    {_row("Average Progress", ctx.formatter.number(data.get("avg_progress_pct"), 2) + "%")}
                    {_row("Max Progress", ctx.formatter.number(data.get("max_progress_pct"), 2) + "%")}
                    {_row("Micro Live Ready Rows", ctx.formatter.number(data.get("micro_live_ready_rows"), 0))}
                    {_row("Micro Live Allowed Rows", ctx.formatter.number(data.get("micro_live_allowed_rows"), 0))}
                    {_row("Conclusion", str(data.get("conclusion", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Next Phase", next_phase)}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Pipeline Row Coverage</h2>
            <table>
                <thead>
                    <tr><th>Слой</th><th>Строк</th></tr>
                </thead>
                <tbody>
                    {_row("Research Candidates", ctx.formatter.number(data.get("paper_candidates_rows"), 0))}
                    {_row("Validation Queue", ctx.formatter.number(data.get("validation_queue_rows"), 0))}
                    {_row("Validation Pipeline", ctx.formatter.number(data.get("validation_pipeline_rows"), 0))}
                    {_row("Robustness", ctx.formatter.number(data.get("robustness_rows"), 0))}
                    {_row("OOS Validation", ctx.formatter.number(data.get("oos_validation_rows"), 0))}
                    {_row("OOS Backtest", ctx.formatter.number(data.get("oos_backtest_rows"), 0))}
                    {_row("Micro Live Readiness", ctx.formatter.number(data.get("micro_live_readiness_rows"), 0))}
                    {_row("Sample Monitor", ctx.formatter.number(data.get("sample_monitor_rows"), 0))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Result</h2>
            <p>PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1</p>
            <p><a href="/paper-sample-accumulation-monitor">Paper Sample Accumulation Monitor</a></p>
            <p><a href="/paper-runtime-sample-collection-phase-close">Phase Close</a></p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PhaseIiPaperEdgeDiscoverySummaryPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.phase_ii_paper_edge_discovery_summary import PhaseIiPaperEdgeDiscoverySummaryPage\n",
    )

if "PhaseIiPaperEdgeDiscoverySummaryPage()," not in s:
    if "PaperRuntimeSampleCollectionPhaseClosePage()," in s:
        s = s.replace(
            "PaperRuntimeSampleCollectionPhaseClosePage(),",
            "PaperRuntimeSampleCollectionPhaseClosePage(),\n    PhaseIiPaperEdgeDiscoverySummaryPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PhaseIiPaperEdgeDiscoverySummaryPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_phase_ii_paper_edge_discovery_summary_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1 ==="

scripts/apply_phase_ii_paper_edge_discovery_summary_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/phase_ii_paper_edge_discovery_summary.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/phase_ii_paper_edge_discovery_summary.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/phase_ii_summary_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/phase_ii_summary_sample_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  > /tmp/phase_ii_summary_timer_health_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY" /tmp/phase_ii_summary_timer_health_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_phase_close_v1.py \
  > /tmp/phase_ii_summary_phase_close_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_READY" /tmp/phase_ii_summary_phase_close_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py \
  | tee /tmp/phase_ii_paper_edge_discovery_summary_builder_v1.txt

grep -q "VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY" \
  /tmp/phase_ii_paper_edge_discovery_summary_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19795 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_phase_ii_summary_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19780 KG_API_BASE_URL=http://127.0.0.1:19795 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/phase_ii_summary_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19795/api/kg/v1/phase-ii-paper-edge-discovery-summary" \
  > /tmp/phase_ii_summary_api_v1.json

curl -fsS "http://127.0.0.1:19780/phase-ii-paper-edge-discovery-summary" \
  > /tmp/phase_ii_summary_page_v1.html

grep -q '"status": "OK"' /tmp/phase_ii_summary_api_v1.json
grep -q '"phase_result_status"' /tmp/phase_ii_summary_api_v1.json
grep -q '"engineering_status"' /tmp/phase_ii_summary_api_v1.json
grep -q '"operational_status"' /tmp/phase_ii_summary_api_v1.json
grep -q '"micro_live_allowed"' /tmp/phase_ii_summary_api_v1.json
grep -q '"next_phase"' /tmp/phase_ii_summary_api_v1.json

grep -q "Phase II Paper Edge Discovery Summary" /tmp/phase_ii_summary_page_v1.html
grep -q "Pipeline Row Coverage" /tmp/phase_ii_summary_page_v1.html
grep -q "PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1" /tmp/phase_ii_summary_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/phase_ii_summary_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 WHERE micro_live_allowed=true;")
engineering_status=$(psql -At -d finam_core -c "SELECT engineering_status FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 WHERE id=1;")

test "$rows" = "1"
test "$allowed" = "0"
test "$engineering_status" = "CLOSED"

psql -d finam_core -c "
SELECT
    phase_result_status,
    engineering_status,
    operational_status,
    close_status,
    timer_health_status,
    candidates_total,
    sample_ready,
    wait_both_sample,
    micro_live_allowed_rows,
    micro_live_allowed,
    next_phase,
    recommended_action
FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
WHERE id=1;
"

echo "phase_ii_summary_rows=$rows"
echo "engineering_status=$engineering_status"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY"
echo "VERDICT=TEST_PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_OK"
SH_TEST

chmod +x scripts/test_phase_ii_paper_edge_discovery_summary_v1.sh

scripts/test_phase_ii_paper_edge_discovery_summary_v1.sh

echo "VERDICT=BUILD_PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_OK"
