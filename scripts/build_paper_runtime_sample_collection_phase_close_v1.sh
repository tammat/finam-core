#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/021_paper_runtime_sample_collection_phase_close_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_phase_close_v1 (
    id SMALLINT PRIMARY KEY,

    phase_name TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION',
    engineering_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operational_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    wait_both_sample INTEGER NOT NULL DEFAULT 0,
    wait_total_sample INTEGER NOT NULL DEFAULT 0,
    wait_oos_sample INTEGER NOT NULL DEFAULT 0,

    min_remaining_total_trades INTEGER,
    min_remaining_oos_trades INTEGER,
    avg_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,

    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    collection_phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    timer_healthy BOOLEAN NOT NULL DEFAULT false,
    service_healthy BOOLEAN NOT NULL DEFAULT false,
    sample_summary_stale BOOLEAN NOT NULL DEFAULT true,
    sample_summary_age_sec INTEGER,

    micro_live_ready_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    close_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    close_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    next_phase TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_phase_close_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_runtime_sample_collection_phase_close_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/021_paper_runtime_sample_collection_phase_close_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_runtime_sample_collection_phase_close_v1.sh

cat > src/scripts/build_paper_runtime_sample_collection_phase_close_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1 ===")

            cur.execute("""
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
                    micro_live_allowed
                FROM marketcore_ui.paper_runtime_sample_collection_v1
                WHERE id=1;
            """)
            collection = cur.fetchone()
            if collection is None:
                raise RuntimeError("marketcore_ui.paper_runtime_sample_collection_v1 id=1 not found")

            collection = dict(collection)

            cur.execute("""
                SELECT
                    timer_health_status,
                    timer_healthy,
                    service_healthy,
                    sample_summary_stale,
                    sample_summary_age_sec,
                    micro_live_allowed
                FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
                WHERE id=1;
            """)
            timer = cur.fetchone()
            if timer is None:
                raise RuntimeError("marketcore_ui.paper_runtime_sample_collection_timer_health_v1 id=1 not found")

            timer = dict(timer)

            cur.execute("""
                SELECT count(*) AS ready_rows
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_ready=true;
            """)
            micro_live_ready_rows = int(cur.fetchone()["ready_rows"] or 0)

            cur.execute("""
                SELECT count(*) AS allowed_rows
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_allowed=true;
            """)
            micro_live_allowed_rows = int(cur.fetchone()["allowed_rows"] or 0)

            candidates_total = int(collection["candidates_total"] or 0)
            sample_ready = int(collection["sample_ready"] or 0)
            wait_both_sample = int(collection["wait_both_sample"] or 0)
            wait_total_sample = int(collection["wait_total_sample"] or 0)
            wait_oos_sample = int(collection["wait_oos_sample"] or 0)

            timer_health_status = str(timer["timer_health_status"] or "UNKNOWN")
            timer_healthy = bool(timer["timer_healthy"] or False)
            service_healthy = bool(timer["service_healthy"] or False)
            sample_summary_stale = bool(timer["sample_summary_stale"] or False)
            micro_live_allowed = bool(collection["micro_live_allowed"] or False) or micro_live_allowed_rows > 0

            if micro_live_allowed:
                engineering_status = "BLOCKED"
                operational_status = "ERROR"
                close_status = "FAILED"
                close_reason = "micro_live_allowed unexpectedly true"
                recommended_action = "Остановить продвижение и проверить risk gates."
                next_phase = "MANUAL_RISK_REVIEW_REQUIRED"
            elif not timer_healthy or not service_healthy or timer_health_status not in {"HEALTHY", "STALE"}:
                engineering_status = "BLOCKED"
                operational_status = "TIMER_UNHEALTHY"
                close_status = "FAILED"
                close_reason = "sample collection timer/service unhealthy"
                recommended_action = "Проверить timer health и journalctl."
                next_phase = "TIMER_HEALTH_FIX"
            elif sample_summary_stale:
                engineering_status = "BLOCKED"
                operational_status = "STALE_SAMPLE_SUMMARY"
                close_status = "FAILED"
                close_reason = "sample summary is stale"
                recommended_action = "Запустить paper sample collection cycle вручную и проверить timer."
                next_phase = "TIMER_HEALTH_FIX"
            elif candidates_total <= 0:
                engineering_status = "CLOSED"
                operational_status = "NO_CANDIDATES"
                close_status = "CLOSED_NO_CANDIDATES"
                close_reason = "phase infrastructure is ready, but no candidates exist"
                recommended_action = "Продолжить Paper Runtime и Research Candidate generation."
                next_phase = "PAPER_RUNTIME_SAMPLE_COLLECTION"
            elif sample_ready > 0:
                engineering_status = "CLOSED"
                operational_status = "READY_FOR_REVALIDATION"
                close_status = "CLOSED_READY_FOR_REVALIDATION"
                close_reason = "one or more candidates reached minimum sample thresholds"
                recommended_action = "Перезапустить Edge Validation Pipeline для sample-ready кандидатов."
                next_phase = "EDGE_REVALIDATION_ON_SAMPLE_READY"
            else:
                engineering_status = "CLOSED"
                operational_status = "WAIT_SAMPLE"
                close_status = "CLOSED_WAIT_SAMPLE"
                close_reason = "phase is complete; candidates are waiting for Paper/OOS sample accumulation"
                recommended_action = "Продолжить Paper Runtime sample accumulation. Micro Live remains blocked."
                next_phase = "PAPER_RUNTIME_SAMPLE_COLLECTION"

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_sample_collection_phase_close_v1 (
                    id,
                    phase_name,
                    engineering_status,
                    operational_status,
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
                    collection_phase_status,
                    timer_health_status,
                    timer_healthy,
                    service_healthy,
                    sample_summary_stale,
                    sample_summary_age_sec,
                    micro_live_ready_rows,
                    micro_live_allowed_rows,
                    micro_live_allowed,
                    close_status,
                    close_reason,
                    recommended_action,
                    next_phase,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,
                    now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    phase_name=EXCLUDED.phase_name,
                    engineering_status=EXCLUDED.engineering_status,
                    operational_status=EXCLUDED.operational_status,
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
                    collection_phase_status=EXCLUDED.collection_phase_status,
                    timer_health_status=EXCLUDED.timer_health_status,
                    timer_healthy=EXCLUDED.timer_healthy,
                    service_healthy=EXCLUDED.service_healthy,
                    sample_summary_stale=EXCLUDED.sample_summary_stale,
                    sample_summary_age_sec=EXCLUDED.sample_summary_age_sec,
                    micro_live_ready_rows=EXCLUDED.micro_live_ready_rows,
                    micro_live_allowed_rows=EXCLUDED.micro_live_allowed_rows,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
                    close_status=EXCLUDED.close_status,
                    close_reason=EXCLUDED.close_reason,
                    recommended_action=EXCLUDED.recommended_action,
                    next_phase=EXCLUDED.next_phase,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                "PAPER_RUNTIME_SAMPLE_COLLECTION",
                engineering_status,
                operational_status,
                candidates_total,
                sample_ready,
                wait_both_sample,
                wait_total_sample,
                wait_oos_sample,
                collection["min_remaining_total_trades"],
                collection["min_remaining_oos_trades"],
                collection["avg_progress_pct"],
                collection["max_progress_pct"],
                collection["collection_status"],
                collection["phase_status"],
                timer_health_status,
                timer_healthy,
                service_healthy,
                sample_summary_stale,
                timer["sample_summary_age_sec"],
                micro_live_ready_rows,
                micro_live_allowed_rows,
                micro_live_allowed,
                close_status,
                close_reason,
                recommended_action,
                next_phase,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"engineering_status={engineering_status}")
    print(f"operational_status={operational_status}")
    print(f"close_status={close_status}")
    print(f"candidates_total={candidates_total}")
    print(f"sample_ready={sample_ready}")
    print(f"wait_both_sample={wait_both_sample}")
    print(f"timer_health_status={timer_health_status}")
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
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-runtime-sample-collection-phase-close' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-runtime-sample-collection-phase-close":
                row = fetch_one("""
                    SELECT
                        phase_name,
                        engineering_status,
                        operational_status,
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
                        collection_phase_status,
                        timer_health_status,
                        timer_healthy,
                        service_healthy,
                        sample_summary_stale,
                        sample_summary_age_sec,
                        micro_live_ready_rows,
                        micro_live_allowed_rows,
                        micro_live_allowed,
                        close_status,
                        close_reason,
                        recommended_action,
                        next_phase,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_sample_collection_phase_close_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_phase_close_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_phase_close_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_runtime_sample_collection_phase_close.py <<'PY'
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


class PaperRuntimeSampleCollectionPhaseClosePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-runtime-sample-collection-phase-close",
            title="Paper Runtime Sample Collection Phase Close",
            icon="✓",
            menu_order=24,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-runtime-sample-collection-phase-close")
        data = payload.get("data") or {}

        engineering_status = str(data.get("engineering_status", "UNKNOWN"))
        operational_status = str(data.get("operational_status", "UNKNOWN"))
        close_status = str(data.get("close_status", "UNKNOWN"))
        next_phase = str(data.get("next_phase", ""))

        candidates_total = ctx.formatter.number(data.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(data.get("sample_ready"), 0)
        wait_both = ctx.formatter.number(data.get("wait_both_sample"), 0)
        min_total = ctx.formatter.number(data.get("min_remaining_total_trades"), 0)
        min_oos = ctx.formatter.number(data.get("min_remaining_oos_trades"), 0)

        return f"""
        <section class="card">
            <h2>Paper Runtime Sample Collection Phase Close</h2>
            <p>Фиксация завершения инженерной фазы Paper Edge Discovery / Sample Collection.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_phase_close_v1.</p>
            <p><a href="/paper-sample-accumulation-monitor">← Sample Monitor</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Engineering", engineering_status)}
            {_metric("Operational", operational_status)}
            {_metric("Close", close_status)}
            {_metric("Candidates", candidates_total)}
            {_metric("Sample Ready", sample_ready)}
        </div>

        <section class="card">
            <h2>Phase Close Summary</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Phase Name", str(data.get("phase_name", "")))}
                    {_row("Engineering Status", engineering_status)}
                    {_row("Operational Status", operational_status)}
                    {_row("Close Status", close_status)}
                    {_row("Close Reason", str(data.get("close_reason", "")))}
                    {_row("Candidates Total", candidates_total)}
                    {_row("Sample Ready", sample_ready)}
                    {_row("Wait Both Sample", wait_both)}
                    {_row("Min Remaining Total Trades", min_total)}
                    {_row("Min Remaining OOS Trades", min_oos)}
                    {_row("Timer Health", str(data.get("timer_health_status", "")))}
                    {_row("Timer Healthy", str(data.get("timer_healthy", "")))}
                    {_row("Service Healthy", str(data.get("service_healthy", "")))}
                    {_row("Summary Stale", str(data.get("sample_summary_stale", "")))}
                    {_row("Micro Live Ready Rows", ctx.formatter.number(data.get("micro_live_ready_rows"), 0))}
                    {_row("Micro Live Allowed Rows", ctx.formatter.number(data.get("micro_live_allowed_rows"), 0))}
                    {_row("Micro Live Allowed", str(data.get("micro_live_allowed", "")))}
                    {_row("Recommended Action", str(data.get("recommended_action", "")))}
                    {_row("Next Phase", next_phase)}
                    {_row("Refreshed At", ctx.formatter.datetime(data.get("refreshed_at")))}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Result</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1</p>
            <p>Текущая фаза закрыта как инженерный контур. Операционный статус зависит от накопления Paper/OOS выборки.</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperRuntimeSampleCollectionPhaseClosePage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_runtime_sample_collection_phase_close import PaperRuntimeSampleCollectionPhaseClosePage\n",
    )

if "PaperRuntimeSampleCollectionPhaseClosePage()," not in s:
    if "PaperSampleCollectionTimerHealthPage()," in s:
        s = s.replace(
            "PaperSampleCollectionTimerHealthPage(),",
            "PaperSampleCollectionTimerHealthPage(),\n    PaperRuntimeSampleCollectionPhaseClosePage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperRuntimeSampleCollectionPhaseClosePage(),",
        )

p.write_text(s)
PY

cat > scripts/test_paper_runtime_sample_collection_phase_close_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1 ==="

scripts/apply_paper_runtime_sample_collection_phase_close_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_phase_close_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_runtime_sample_collection_phase_close.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_runtime_sample_collection_phase_close.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/phase_close_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/phase_close_sample_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  > /tmp/phase_close_timer_health_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY" /tmp/phase_close_timer_health_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_phase_close_v1.py \
  | tee /tmp/phase_close_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_READY" /tmp/phase_close_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19695 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_phase_close_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19680 KG_API_BASE_URL=http://127.0.0.1:19695 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/phase_close_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19695/api/kg/v1/paper-runtime-sample-collection-phase-close" \
  > /tmp/phase_close_api_v1.json

curl -fsS "http://127.0.0.1:19680/paper-runtime-sample-collection-phase-close" \
  > /tmp/phase_close_page_v1.html

grep -q '"status": "OK"' /tmp/phase_close_api_v1.json
grep -q '"engineering_status"' /tmp/phase_close_api_v1.json
grep -q '"operational_status"' /tmp/phase_close_api_v1.json
grep -q '"close_status"' /tmp/phase_close_api_v1.json
grep -q '"micro_live_allowed"' /tmp/phase_close_api_v1.json
grep -q '"next_phase"' /tmp/phase_close_api_v1.json

grep -q "Paper Runtime Sample Collection Phase Close" /tmp/phase_close_page_v1.html
grep -q "Phase Close Summary" /tmp/phase_close_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1" /tmp/phase_close_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/phase_close_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_phase_close_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_phase_close_v1 WHERE micro_live_allowed=true;")
engineering_status=$(psql -At -d finam_core -c "SELECT engineering_status FROM marketcore_ui.paper_runtime_sample_collection_phase_close_v1 WHERE id=1;")

test "$rows" = "1"
test "$allowed" = "0"
test "$engineering_status" = "CLOSED"

psql -d finam_core -c "
SELECT
    engineering_status,
    operational_status,
    close_status,
    candidates_total,
    sample_ready,
    wait_both_sample,
    timer_health_status,
    micro_live_allowed_rows,
    micro_live_allowed,
    next_phase,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_phase_close_v1
WHERE id=1;
"

echo "phase_close_rows=$rows"
echo "engineering_status=$engineering_status"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_OK"
SH_TEST

chmod +x scripts/test_paper_runtime_sample_collection_phase_close_v1.sh

scripts/test_paper_runtime_sample_collection_phase_close_v1.sh

echo "VERDICT=BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_OK"
