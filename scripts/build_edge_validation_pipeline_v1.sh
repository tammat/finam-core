#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_VALIDATION_PIPELINE_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/013_edge_validation_pipeline_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_validation_pipeline_v1 (
    pipeline_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',
    queue_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    priority TEXT NOT NULL DEFAULT 'NORMAL',

    sample_check_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    pf_check_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    expectancy_check_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_status TEXT NOT NULL DEFAULT 'PENDING',
    oos_status TEXT NOT NULL DEFAULT 'PENDING',

    pipeline_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',

    expectancy NUMERIC(20,6),
    profit_factor NUMERIC(20,6),
    winrate NUMERIC(20,6),
    trades INTEGER,
    net_pnl NUMERIC(20,6),
    score NUMERIC(20,6),

    evidence_summary TEXT NOT NULL DEFAULT '',
    risk_notes TEXT NOT NULL DEFAULT '',

    source_queue_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_VALIDATION_PIPELINE_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_validation_pipeline_v1 TO alex;

COMMIT;

SELECT 'EDGE_VALIDATION_PIPELINE_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_edge_validation_pipeline_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/013_edge_validation_pipeline_v1.sql
SH_APPLY

chmod +x scripts/apply_edge_validation_pipeline_v1.sh

cat > src/scripts/build_edge_validation_pipeline_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_VALIDATION_PIPELINE_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict) -> dict:
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))

    sample_check_status = "PASS" if trades >= 30 else "WAIT_SAMPLE"

    if pf >= Decimal("1.2"):
        pf_check_status = "PASS"
    elif pf >= Decimal("1.0"):
        pf_check_status = "WATCH"
    else:
        pf_check_status = "FAIL"

    if expectancy > Decimal("0"):
        expectancy_check_status = "PASS"
    elif expectancy == Decimal("0"):
        expectancy_check_status = "WATCH"
    else:
        expectancy_check_status = "FAIL"

    if trades < 30:
        pipeline_status = "ACCUMULATE_SAMPLE"
        recommended_action = "Накопить выборку Paper Runtime до 30+ сделок."
        robustness_status = "WAITING"
        oos_status = "WAITING"
    elif pf >= Decimal("1.2") and expectancy > Decimal("0"):
        pipeline_status = "READY_FOR_ROBUSTNESS"
        recommended_action = "Запустить robustness-проверку кандидата."
        robustness_status = "REQUIRED"
        oos_status = "WAITING"
    elif pf >= Decimal("1.0") and expectancy >= Decimal("0"):
        pipeline_status = "OBSERVE_MORE"
        recommended_action = "Продолжить наблюдение и проверить устойчивость по времени."
        robustness_status = "WAITING"
        oos_status = "WAITING"
    else:
        pipeline_status = "REJECTED_BY_RULES"
        recommended_action = "Не продвигать кандидата без дополнительного анализа."
        robustness_status = "NOT_ALLOWED"
        oos_status = "NOT_ALLOWED"

    return {
        "sample_check_status": sample_check_status,
        "pf_check_status": pf_check_status,
        "expectancy_check_status": expectancy_check_status,
        "robustness_status": robustness_status,
        "oos_status": oos_status,
        "pipeline_status": pipeline_status,
        "recommended_action": recommended_action,
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_VALIDATION_PIPELINE_V1 ===")

            cur.execute("""
                SELECT
                    queue_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    validation_status,
                    priority,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    evidence_summary,
                    risk_notes
                FROM marketcore_ui.edge_validation_queue_v1
                ORDER BY
                    CASE
                        WHEN validation_status='READY_FOR_EDGE_VALIDATION' THEN 1
                        WHEN validation_status='WATCHLIST' THEN 2
                        WHEN validation_status='ACCUMULATE_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    queue_rank;
            """)
            queue_rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_validation_pipeline_v1;")

            for idx, row in enumerate(queue_rows, start=1):
                c = classify(row)

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_validation_pipeline_v1 (
                        pipeline_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        queue_status,
                        priority,
                        sample_check_status,
                        pf_check_status,
                        expectancy_check_status,
                        robustness_status,
                        oos_status,
                        pipeline_status,
                        recommended_action,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        source_queue_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("validation_status") or "UNKNOWN",
                    row.get("priority") or "NORMAL",
                    c["sample_check_status"],
                    c["pf_check_status"],
                    c["expectancy_check_status"],
                    c["robustness_status"],
                    c["oos_status"],
                    c["pipeline_status"],
                    c["recommended_action"],
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    row.get("evidence_summary") or "",
                    row.get("risk_notes") or "",
                    row.get("queue_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_validation_pipeline_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT pipeline_status, count(*) AS rows
                FROM marketcore_ui.edge_validation_pipeline_v1
                GROUP BY pipeline_status
                ORDER BY pipeline_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"pipeline_status_{row['pipeline_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/edge-validation-pipeline' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/edge-validation-pipeline":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        pipeline_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        queue_status,
                        priority,
                        sample_check_status,
                        pf_check_status,
                        expectancy_check_status,
                        robustness_status,
                        oos_status,
                        pipeline_status,
                        recommended_action,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        source_queue_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_validation_pipeline_v1
                    ORDER BY pipeline_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_validation_pipeline_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_validation_pipeline_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/edge_validation_pipeline.py <<'PY'
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
        return "<p>Pipeline пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("pipeline_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("pipeline_status", "")))}</td>
            <td>{escape(str(row.get("sample_check_status", "")))}</td>
            <td>{escape(str(row.get("pf_check_status", "")))}</td>
            <td>{escape(str(row.get("expectancy_check_status", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(str(row.get("oos_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("trades"), 0))}</td>
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
                <th>Pipeline</th>
                <th>Sample</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>Robustness</th>
                <th>OOS</th>
                <th>PF</th>
                <th>Exp.</th>
                <th>Trades</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeValidationPipelinePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-validation-pipeline",
            title="Edge Validation Pipeline",
            icon="▶",
            menu_order=17,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-validation-pipeline?limit=50")
        rows = payload.get("data") or []

        accumulate = sum(1 for row in rows if row.get("pipeline_status") == "ACCUMULATE_SAMPLE")
        ready = sum(1 for row in rows if row.get("pipeline_status") == "READY_FOR_ROBUSTNESS")
        observe = sum(1 for row in rows if row.get("pipeline_status") == "OBSERVE_MORE")
        rejected = sum(1 for row in rows if row.get("pipeline_status") == "REJECTED_BY_RULES")

        return f"""
        <section class="card">
            <h2>Edge Validation Pipeline</h2>
            <p>Pipeline переводит кандидатов из Edge Validation Queue в формальные статусы проверки.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_validation_pipeline_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready", ctx.formatter.number(ready, 0), "Готовы к robustness")}
            {_metric("Observe", ctx.formatter.number(observe, 0), "Требуют наблюдения")}
            {_metric("Sample", ctx.formatter.number(accumulate, 0), "Накопить выборку")}
            {_metric("Rejected", ctx.formatter.number(rejected, 0), "Не продвигать")}
        </div>

        <section class="card">
            <h2>Pipeline</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_ROBUSTNESS_CHECK_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "EdgeValidationPipelinePage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.edge_validation_pipeline import EdgeValidationPipelinePage\n",
    )

if "EdgeValidationPipelinePage()," not in s:
    if "EdgeValidationQueuePage()," in s:
        s = s.replace(
            "EdgeValidationQueuePage(),",
            "EdgeValidationQueuePage(),\n    EdgeValidationPipelinePage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    EdgeValidationPipelinePage(),",
        )

p.write_text(s)
PY

cat > scripts/test_edge_validation_pipeline_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_PIPELINE_V1 ==="

scripts/apply_edge_validation_pipeline_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_pipeline_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/edge_validation_pipeline.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/edge_validation_pipeline_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/edge_validation_pipeline_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  | tee /tmp/edge_validation_pipeline_builder_v1.txt

grep -q "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY" /tmp/edge_validation_pipeline_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18695 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_edge_validation_pipeline_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18680 KG_API_BASE_URL=http://127.0.0.1:18695 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/edge_validation_pipeline_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18695/api/kg/v1/edge-validation-pipeline?limit=20" \
  > /tmp/edge_validation_pipeline_api_v1.json

curl -fsS "http://127.0.0.1:18680/edge-validation-pipeline" \
  > /tmp/edge_validation_pipeline_page_v1.html

grep -q '"status": "OK"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"pipeline_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"sample_check_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"pf_check_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"expectancy_check_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"recommended_action"' /tmp/edge_validation_pipeline_api_v1.json

grep -q "Edge Validation Pipeline" /tmp/edge_validation_pipeline_page_v1.html
grep -q "Pipeline" /tmp/edge_validation_pipeline_page_v1.html
grep -q "EDGE_ROBUSTNESS_CHECK_V1" /tmp/edge_validation_pipeline_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/edge_validation_pipeline_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_pipeline_v1;")
test "$rows" -gt 0

echo "edge_validation_pipeline_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_PIPELINE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_validation_pipeline_v1.sh

scripts/test_edge_validation_pipeline_v1.sh

echo "VERDICT=BUILD_EDGE_VALIDATION_PIPELINE_V1_OK"
