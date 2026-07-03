#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/023_paper_runtime_sample_collection_operations_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_operations_v1 (
    operation_rank INTEGER PRIMARY KEY,

    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    sample_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    readiness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    backtest_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    total_trades INTEGER NOT NULL DEFAULT 0,
    required_total_trades INTEGER NOT NULL DEFAULT 30,
    remaining_total_trades INTEGER NOT NULL DEFAULT 0,

    oos_trades INTEGER NOT NULL DEFAULT 0,
    required_oos_trades INTEGER NOT NULL DEFAULT 10,
    remaining_oos_trades INTEGER NOT NULL DEFAULT 0,

    progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,

    operation_priority TEXT NOT NULL DEFAULT 'NORMAL',
    operation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operation_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    next_check TEXT NOT NULL DEFAULT '',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    micro_live_ready BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    source_monitor_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_operations_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_runtime_sample_collection_operations_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/023_paper_runtime_sample_collection_operations_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_runtime_sample_collection_operations_v1.sh

cat > src/scripts/build_paper_runtime_sample_collection_operations_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict, timer_health_status: str, collection_status: str, phase_status: str) -> dict:
    remaining_total = int(row.get("remaining_total_trades") or 0)
    remaining_oos = int(row.get("remaining_oos_trades") or 0)
    progress_pct = dec(row.get("progress_pct"))
    sample_status = str(row.get("sample_status") or "UNKNOWN")
    micro_live_allowed = bool(row.get("micro_live_allowed") or False)

    if micro_live_allowed:
        return {
            "operation_priority": "CRITICAL",
            "operation_status": "BLOCKED_MICRO_LIVE_ALLOWED",
            "operation_reason": "micro_live_allowed unexpectedly true",
            "recommended_action": "Остановить продвижение и проверить risk gates.",
            "next_check": "MANUAL_RISK_REVIEW",
        }

    if timer_health_status not in {"HEALTHY", "STALE"}:
        return {
            "operation_priority": "CRITICAL",
            "operation_status": "TIMER_HEALTH_REQUIRED",
            "operation_reason": "sample collection timer/service unhealthy",
            "recommended_action": "Проверить timer health и journalctl.",
            "next_check": "PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1",
        }

    if sample_status == "SAMPLE_READY":
        return {
            "operation_priority": "HIGH",
            "operation_status": "READY_FOR_REVALIDATION",
            "operation_reason": "минимальная выборка набрана",
            "recommended_action": "Перезапустить Edge Validation Pipeline для кандидата.",
            "next_check": "EDGE_REVALIDATION_ON_SAMPLE_READY",
        }

    if remaining_total <= 5 and remaining_oos <= 3:
        return {
            "operation_priority": "HIGH",
            "operation_status": "NEAR_SAMPLE_READY",
            "operation_reason": "кандидат близок к минимальной выборке",
            "recommended_action": "Продолжить Paper Runtime и проверить кандидата после ближайших сделок.",
            "next_check": "PAPER_SAMPLE_ACCUMULATION_MONITOR_V1",
        }

    if progress_pct >= Decimal("70"):
        return {
            "operation_priority": "NORMAL",
            "operation_status": "ACCUMULATING_FAST",
            "operation_reason": "прогресс выборки выше 70%",
            "recommended_action": "Продолжить накопление выборки.",
            "next_check": "PAPER_SAMPLE_ACCUMULATION_MONITOR_V1",
        }

    if collection_status == "COLLECTING" and phase_status == "WAIT_SAMPLE":
        return {
            "operation_priority": "NORMAL",
            "operation_status": "COLLECTING",
            "operation_reason": "кандидат ожидает накопления Paper/OOS выборки",
            "recommended_action": "Продолжить Paper Runtime sample accumulation.",
            "next_check": "PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1",
        }

    return {
        "operation_priority": "LOW",
        "operation_status": "OBSERVE",
        "operation_reason": "операционный статус требует наблюдения",
        "recommended_action": "Проверить summary и monitor.",
        "next_check": "PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1",
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1 ===")

            cur.execute("""
                SELECT
                    timer_health_status,
                    collection_status,
                    phase_status,
                    micro_live_allowed
                FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
                WHERE id=1;
            """)
            health = cur.fetchone()
            if health is None:
                raise RuntimeError("timer health row id=1 not found")

            health = dict(health)
            timer_health_status = str(health.get("timer_health_status") or "UNKNOWN")

            cur.execute("""
                SELECT
                    collection_status,
                    phase_status
                FROM marketcore_ui.paper_runtime_sample_collection_v1
                WHERE id=1;
            """)
            summary = cur.fetchone()
            if summary is None:
                raise RuntimeError("sample collection summary id=1 not found")

            summary = dict(summary)
            collection_status = str(summary.get("collection_status") or "UNKNOWN")
            phase_status = str(summary.get("phase_status") or "UNKNOWN")

            cur.execute("""
                SELECT
                    monitor_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    readiness_status,
                    backtest_status,
                    oos_status,
                    robustness_status,
                    total_trades,
                    required_total_trades,
                    remaining_total_trades,
                    oos_trades,
                    required_oos_trades,
                    remaining_oos_trades,
                    sample_status,
                    progress_pct,
                    micro_live_ready,
                    micro_live_allowed,
                    recommended_action
                FROM marketcore_ui.paper_sample_accumulation_monitor_v1
                ORDER BY
                    CASE
                        WHEN sample_status='SAMPLE_READY' THEN 1
                        WHEN remaining_total_trades <= 5 AND remaining_oos_trades <= 3 THEN 2
                        WHEN progress_pct >= 70 THEN 3
                        ELSE 4
                    END,
                    remaining_total_trades,
                    remaining_oos_trades,
                    monitor_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row, timer_health_status, collection_status, phase_status)

                cur.execute("""
                    INSERT INTO marketcore_ui.paper_runtime_sample_collection_operations_v1 (
                        operation_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        sample_status,
                        readiness_status,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        total_trades,
                        required_total_trades,
                        remaining_total_trades,
                        oos_trades,
                        required_oos_trades,
                        remaining_oos_trades,
                        progress_pct,
                        operation_priority,
                        operation_status,
                        operation_reason,
                        recommended_action,
                        next_check,
                        timer_health_status,
                        collection_status,
                        phase_status,
                        micro_live_ready,
                        micro_live_allowed,
                        source_monitor_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("sample_status") or "UNKNOWN",
                    row.get("readiness_status") or "UNKNOWN",
                    row.get("backtest_status") or "UNKNOWN",
                    row.get("oos_status") or "UNKNOWN",
                    row.get("robustness_status") or "UNKNOWN",
                    row.get("total_trades") or 0,
                    row.get("required_total_trades") or 30,
                    row.get("remaining_total_trades") or 0,
                    row.get("oos_trades") or 0,
                    row.get("required_oos_trades") or 10,
                    row.get("remaining_oos_trades") or 0,
                    row.get("progress_pct") or 0,
                    c["operation_priority"],
                    c["operation_status"],
                    c["operation_reason"],
                    c["recommended_action"],
                    c["next_check"],
                    timer_health_status,
                    collection_status,
                    phase_status,
                    bool(row.get("micro_live_ready") or False),
                    bool(row.get("micro_live_allowed") or False),
                    row.get("monitor_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT operation_status, count(*) AS rows
                FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
                GROUP BY operation_status
                ORDER BY operation_status;
            """)
            status_rows = cur.fetchall()

            cur.execute("""
                SELECT count(*) AS allowed
                FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
                WHERE micro_live_allowed=true;
            """)
            allowed_rows = int(cur.fetchone()["allowed"])

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"operation_status_{row['operation_status']}={row['rows']}")
    print(f"micro_live_allowed_rows={allowed_rows}")
    print(f"timer_health_status={timer_health_status}")
    print(f"collection_status={collection_status}")
    print(f"phase_status={phase_status}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-runtime-sample-collection-operations' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-runtime-sample-collection-operations":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        operation_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        sample_status,
                        readiness_status,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        total_trades,
                        required_total_trades,
                        remaining_total_trades,
                        oos_trades,
                        required_oos_trades,
                        remaining_oos_trades,
                        progress_pct,
                        operation_priority,
                        operation_status,
                        operation_reason,
                        recommended_action,
                        next_check,
                        timer_health_status,
                        collection_status,
                        phase_status,
                        micro_live_ready,
                        micro_live_allowed,
                        source_monitor_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
                    ORDER BY operation_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_runtime_sample_collection_operations_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_runtime_sample_collection_operations_v1",
                    "orders_changed": 0,
                    "execution_changed": 0
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_runtime_sample_collection_operations.py <<'PY'
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


def _table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Operations пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("operation_rank", "")))}</td>
            <td>{escape(str(row.get("operation_priority", "")))}</td>
            <td>{escape(str(row.get("operation_status", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("sample_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("progress_pct"), 2))}%</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("remaining_oos_trades"), 0))}</td>
            <td>{escape(str(row.get("operation_reason", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
            <td>{escape(str(row.get("next_check", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Инструмент</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Sample</th>
                <th>Progress</th>
                <th>Need Total</th>
                <th>Need OOS</th>
                <th>Причина</th>
                <th>Действие</th>
                <th>Next Check</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperRuntimeSampleCollectionOperationsPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-runtime-sample-collection-operations",
            title="Paper Runtime Sample Collection Operations",
            icon="□",
            menu_order=26,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-runtime-sample-collection-operations?limit=50")
        rows = payload.get("data") or []

        high = sum(1 for row in rows if row.get("operation_priority") == "HIGH")
        normal = sum(1 for row in rows if row.get("operation_priority") == "NORMAL")
        collecting = sum(1 for row in rows if row.get("operation_status") == "COLLECTING")
        near = sum(1 for row in rows if row.get("operation_status") == "NEAR_SAMPLE_READY")
        allowed = sum(1 for row in rows if row.get("micro_live_allowed") is True)

        return f"""
        <section class="card">
            <h2>Paper Runtime Sample Collection Operations</h2>
            <p>Ежедневная операционная очередь: что делать с кандидатами, ожидающими накопления Paper/OOS выборки.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_runtime_sample_collection_operations_v1.</p>
            <p><a href="/phase-ii-paper-edge-discovery-summary">← Phase II Summary</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("High", ctx.formatter.number(high, 0))}
            {_metric("Normal", ctx.formatter.number(normal, 0))}
            {_metric("Collecting", ctx.formatter.number(collecting, 0))}
            {_metric("Near Ready", ctx.formatter.number(near, 0))}
        </div>

        <section class="card">
            <h2>Safety</h2>
            <p>micro_live_allowed_rows={escape(ctx.formatter.number(allowed, 0))}</p>
        </section>

        <section class="card">
            <h2>Operations Queue</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperRuntimeSampleCollectionOperationsPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_runtime_sample_collection_operations import PaperRuntimeSampleCollectionOperationsPage\n",
    )

if "PaperRuntimeSampleCollectionOperationsPage()," not in s:
    if "PhaseIiPaperEdgeDiscoverySummaryPage()," in s:
        s = s.replace(
            "PhaseIiPaperEdgeDiscoverySummaryPage(),",
            "PhaseIiPaperEdgeDiscoverySummaryPage(),\n    PaperRuntimeSampleCollectionOperationsPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperRuntimeSampleCollectionOperationsPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_paper_runtime_sample_collection_operations_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1 ==="

scripts/apply_paper_runtime_sample_collection_operations_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_operations_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_runtime_sample_collection_operations.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_runtime_sample_collection_operations.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/operations_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/operations_sample_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  > /tmp/operations_timer_health_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY" /tmp/operations_timer_health_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py \
  > /tmp/operations_phase_summary_v1.log

grep -q "VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY" /tmp/operations_phase_summary_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_operations_v1.py \
  | tee /tmp/paper_runtime_sample_collection_operations_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_READY" \
  /tmp/paper_runtime_sample_collection_operations_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19895 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_operations_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19880 KG_API_BASE_URL=http://127.0.0.1:19895 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/operations_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19895/api/kg/v1/paper-runtime-sample-collection-operations?limit=20" \
  > /tmp/operations_api_v1.json

curl -fsS "http://127.0.0.1:19880/paper-runtime-sample-collection-operations" \
  > /tmp/operations_page_v1.html

grep -q '"status": "OK"' /tmp/operations_api_v1.json
grep -q '"operation_status"' /tmp/operations_api_v1.json
grep -q '"operation_priority"' /tmp/operations_api_v1.json
grep -q '"recommended_action"' /tmp/operations_api_v1.json
grep -q '"micro_live_allowed"' /tmp/operations_api_v1.json

grep -q "Paper Runtime Sample Collection Operations" /tmp/operations_page_v1.html
grep -q "Operations Queue" /tmp/operations_page_v1.html
grep -q "micro_live_allowed_rows=0" /tmp/operations_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_V1" /tmp/operations_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/operations_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_v1 WHERE micro_live_allowed=true;")

test "$rows" -gt 0
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    operation_priority,
    operation_status,
    count(*) AS rows
FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
GROUP BY operation_priority, operation_status
ORDER BY operation_priority, operation_status;
"

echo "operations_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_OK"
SH_TEST

chmod +x scripts/test_paper_runtime_sample_collection_operations_v1.sh

scripts/test_paper_runtime_sample_collection_operations_v1.sh

echo "VERDICT=BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_OK"
