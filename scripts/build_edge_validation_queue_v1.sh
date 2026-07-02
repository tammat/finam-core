#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_VALIDATION_QUEUE_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/012_edge_validation_queue_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_validation_queue_v1 (
    queue_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',
    candidate_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    expectancy NUMERIC(20,6),
    profit_factor NUMERIC(20,6),
    winrate NUMERIC(20,6),
    trades INTEGER,
    net_pnl NUMERIC(20,6),
    score NUMERIC(20,6),
    evidence_summary TEXT NOT NULL DEFAULT '',
    risk_notes TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    source_candidate_rank INTEGER,
    source_table TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'EDGE_VALIDATION_QUEUE_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_validation_queue_v1 TO alex;

COMMIT;

SELECT 'EDGE_VALIDATION_QUEUE_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_edge_validation_queue_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/012_edge_validation_queue_v1.sql
SH_APPLY

chmod +x scripts/apply_edge_validation_queue_v1.sh

cat > src/scripts/build_edge_validation_queue_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_VALIDATION_QUEUE_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def status_for(row: dict) -> tuple[str, str, str, str]:
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))

    if trades < 30:
        return (
            "ACCUMULATE_SAMPLE",
            "LOW",
            "Накопить выборку Paper Runtime",
            "Выборка меньше 30 сделок; статистическая устойчивость не подтверждена.",
        )

    if pf >= Decimal("1.2") and expectancy > Decimal("0"):
        return (
            "READY_FOR_EDGE_VALIDATION",
            "HIGH",
            "Передать в Edge Validation",
            "PF выше минимального порога и expectancy положительное; требуется устойчивость и OOS.",
        )

    if pf >= Decimal("1.0") and expectancy >= Decimal("0"):
        return (
            "WATCHLIST",
            "NORMAL",
            "Наблюдать и проверить устойчивость",
            "Результат не отрицательный, но запас преимущества недостаточен для немедленного продвижения.",
        )

    return (
        "REJECT_REVIEW",
        "LOW",
        "Не продвигать без дополнительного анализа",
        "Текущая статистика не подтверждает edge.",
    )


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_VALIDATION_QUEUE_V1 ===")

            cur.execute("""
                SELECT
                    candidate_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    candidate_status,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    source_table,
                    refreshed_at
                FROM marketcore_ui.paper_edge_research_candidates_v1
                ORDER BY
                    CASE
                        WHEN COALESCE(trades,0) >= 30
                         AND COALESCE(profit_factor,0) >= 1.2
                         AND COALESCE(expectancy,0) > 0 THEN 1
                        WHEN COALESCE(trades,0) >= 30
                         AND COALESCE(profit_factor,0) >= 1.0
                         AND COALESCE(expectancy,0) >= 0 THEN 2
                        WHEN COALESCE(trades,0) < 30 THEN 3
                        ELSE 4
                    END,
                    COALESCE(score,0) DESC,
                    COALESCE(profit_factor,0) DESC,
                    COALESCE(expectancy,0) DESC,
                    candidate_rank
                LIMIT 50;
            """)
            candidates = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_validation_queue_v1;")

            for idx, row in enumerate(candidates, start=1):
                validation_status, priority, recommended_action, risk_notes = status_for(row)

                evidence_summary = (
                    f"Trades={row.get('trades') or 0}; "
                    f"PF={row.get('profit_factor') or 0}; "
                    f"Expectancy={row.get('expectancy') or 0}; "
                    f"WinRate={row.get('winrate') or 0}; "
                    f"NetPnL={row.get('net_pnl') or 0}"
                )

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_validation_queue_v1 (
                        queue_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        validation_status,
                        priority,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        recommended_action,
                        source_candidate_rank,
                        source_table,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("candidate_status") or "UNKNOWN",
                    validation_status,
                    priority,
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    evidence_summary,
                    risk_notes,
                    recommended_action,
                    row.get("candidate_rank"),
                    row.get("source_table") or "",
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_validation_queue_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT validation_status, count(*) AS rows
                FROM marketcore_ui.edge_validation_queue_v1
                GROUP BY validation_status
                ORDER BY validation_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"status_{row['validation_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_VALIDATION_QUEUE_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/edge-validation-queue' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/edge-validation-queue":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        queue_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        validation_status,
                        priority,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        recommended_action,
                        source_candidate_rank,
                        source_table,
                        refreshed_at
                    FROM marketcore_ui.edge_validation_queue_v1
                    ORDER BY queue_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_validation_queue_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_validation_queue_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/edge_validation_queue.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Очередь Edge Validation пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("queue_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("validation_status", "")))}</td>
            <td>{escape(str(row.get("priority", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("trades"), 0))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
            <td>{escape(str(row.get("risk_notes", "")))}</td>
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
                <th>Статус</th>
                <th>Priority</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>Trades</th>
                <th>Действие</th>
                <th>Риски</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeValidationQueuePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-validation-queue",
            title="Edge Validation Queue",
            icon="✓",
            menu_order=16,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-validation-queue?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("validation_status") == "READY_FOR_EDGE_VALIDATION")
        watchlist = sum(1 for row in rows if row.get("validation_status") == "WATCHLIST")
        low_sample = sum(1 for row in rows if row.get("validation_status") == "ACCUMULATE_SAMPLE")

        return f"""
        <section class="card">
            <h2>Edge Validation Queue</h2>
            <p>Очередь кандидатов, которые должны пройти следующую проверку перед продвижением к Paper/Micro Live.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_validation_queue_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            <section class="card"><h2>Всего</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(len(rows), 0))}</p></section>
            <section class="card"><h2>Ready</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(ready, 0))}</p></section>
            <section class="card"><h2>Watchlist</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(watchlist, 0))}</p></section>
            <section class="card"><h2>Low Sample</h2><p style="font-size:28px;font-weight:700;">{escape(ctx.formatter.number(low_sample, 0))}</p></section>
        </div>

        <section class="card">
            <h2>Queue</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_VALIDATION_PIPELINE_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "EdgeValidationQueuePage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.edge_validation_queue import EdgeValidationQueuePage\n",
    )

if "EdgeValidationQueuePage()," not in s:
    if "PaperEdgeDiscoveryPage()," in s:
        s = s.replace(
            "PaperEdgeDiscoveryPage(),",
            "PaperEdgeDiscoveryPage(),\n    EdgeValidationQueuePage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    EdgeValidationQueuePage(),",
        )

p.write_text(s)
PY

cat > scripts/test_edge_validation_queue_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_QUEUE_V1 ==="

scripts/apply_edge_validation_queue_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_queue_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/edge_validation_queue.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/edge_validation_queue_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  | tee /tmp/edge_validation_queue_builder_v1.txt

grep -q "VERDICT=EDGE_VALIDATION_QUEUE_V1_READY" /tmp/edge_validation_queue_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18595 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_edge_validation_queue_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18580 KG_API_BASE_URL=http://127.0.0.1:18595 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/edge_validation_queue_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18595/api/kg/v1/edge-validation-queue?limit=20" \
  > /tmp/edge_validation_queue_api_v1.json

curl -fsS "http://127.0.0.1:18580/edge-validation-queue" \
  > /tmp/edge_validation_queue_page_v1.html

grep -q '"status": "OK"' /tmp/edge_validation_queue_api_v1.json
grep -q '"validation_status"' /tmp/edge_validation_queue_api_v1.json
grep -q '"recommended_action"' /tmp/edge_validation_queue_api_v1.json

grep -q "Edge Validation Queue" /tmp/edge_validation_queue_page_v1.html
grep -q "Queue" /tmp/edge_validation_queue_page_v1.html
grep -q "EDGE_VALIDATION_PIPELINE_V1" /tmp/edge_validation_queue_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/edge_validation_queue_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_queue_v1;")
test "$rows" -gt 0

echo "edge_validation_queue_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_VALIDATION_QUEUE_V1_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_QUEUE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_validation_queue_v1.sh

scripts/test_edge_validation_queue_v1.sh

echo "VERDICT=BUILD_EDGE_VALIDATION_QUEUE_V1_OK"
