#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_OOS_VALIDATION_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/015_edge_oos_validation_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_oos_validation_v1 (
    oos_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_readiness TEXT NOT NULL DEFAULT 'UNKNOWN',

    sample_size_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    pf_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    expectancy_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    winrate_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    pnl_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    robustness_score NUMERIC(20,6) NOT NULL DEFAULT 0,
    oos_required BOOLEAN NOT NULL DEFAULT false,
    micro_live_ready BOOLEAN NOT NULL DEFAULT false,

    expectancy NUMERIC(20,6),
    profit_factor NUMERIC(20,6),
    winrate NUMERIC(20,6),
    trades INTEGER,
    net_pnl NUMERIC(20,6),
    score NUMERIC(20,6),

    evidence_summary TEXT NOT NULL DEFAULT '',
    oos_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_robustness_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_OOS_VALIDATION_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_oos_validation_v1 TO alex;

COMMIT;

SELECT 'EDGE_OOS_VALIDATION_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_edge_oos_validation_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/015_edge_oos_validation_v1.sql
SH_APPLY

chmod +x scripts/apply_edge_oos_validation_v1.sh

cat > src/scripts/build_edge_oos_validation_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_OOS_VALIDATION_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict) -> dict:
    robustness_status = str(row.get("robustness_status") or "UNKNOWN")
    robustness_score = dec(row.get("robustness_score"))
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))

    if robustness_status == "WAIT_SAMPLE":
        return {
            "oos_status": "WAIT_SAMPLE",
            "oos_readiness": "NOT_READY",
            "micro_live_ready": False,
            "oos_reason": "Недостаточная выборка. OOS-проверка преждевременна.",
            "recommended_action": "Накопить выборку Paper Runtime.",
        }

    if robustness_status == "ROBUSTNESS_REQUIRED":
        if robustness_score >= Decimal("0.75") and trades >= 30 and pf >= Decimal("1.2") and expectancy > Decimal("0"):
            return {
                "oos_status": "READY_FOR_OOS",
                "oos_readiness": "READY",
                "micro_live_ready": False,
                "oos_reason": "Кандидат прошёл первичные robustness-фильтры и готов к out-of-sample проверке.",
                "recommended_action": "Запустить EDGE_OOS_BACKTEST_V1.",
            }

        return {
            "oos_status": "ROBUSTNESS_WEAK",
            "oos_readiness": "NOT_READY",
            "micro_live_ready": False,
            "oos_reason": "Robustness-score недостаточен для OOS.",
            "recommended_action": "Продолжить robustness-анализ.",
        }

    if robustness_status == "WATCHLIST":
        return {
            "oos_status": "OBSERVE_MORE",
            "oos_readiness": "WATCH",
            "micro_live_ready": False,
            "oos_reason": "Кандидат требует дополнительного наблюдения до OOS.",
            "recommended_action": "Продолжить наблюдение и накопление данных.",
        }

    return {
        "oos_status": "BLOCKED_BY_ROBUSTNESS",
        "oos_readiness": "BLOCKED",
        "micro_live_ready": False,
        "oos_reason": "Кандидат не прошёл robustness-фильтры.",
        "recommended_action": "Не продвигать в OOS.",
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_OOS_VALIDATION_V1 ===")

            cur.execute("""
                SELECT
                    robustness_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    robustness_status,
                    sample_size_status,
                    pf_status,
                    expectancy_status,
                    winrate_status,
                    pnl_status,
                    robustness_score,
                    oos_required,
                    micro_live_ready,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    evidence_summary,
                    weakness_summary,
                    recommended_action
                FROM marketcore_ui.edge_robustness_check_v1
                ORDER BY
                    CASE
                        WHEN robustness_status='ROBUSTNESS_REQUIRED' THEN 1
                        WHEN robustness_status='WATCHLIST' THEN 2
                        WHEN robustness_status='WAIT_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    robustness_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_oos_validation_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row)

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_oos_validation_v1 (
                        oos_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        robustness_status,
                        oos_status,
                        oos_readiness,
                        sample_size_status,
                        pf_status,
                        expectancy_status,
                        winrate_status,
                        pnl_status,
                        robustness_score,
                        oos_required,
                        micro_live_ready,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        oos_reason,
                        recommended_action,
                        source_robustness_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("robustness_status") or "UNKNOWN",
                    c["oos_status"],
                    c["oos_readiness"],
                    row.get("sample_size_status") or "UNKNOWN",
                    row.get("pf_status") or "UNKNOWN",
                    row.get("expectancy_status") or "UNKNOWN",
                    row.get("winrate_status") or "UNKNOWN",
                    row.get("pnl_status") or "UNKNOWN",
                    row.get("robustness_score") or 0,
                    row.get("oos_required") or False,
                    c["micro_live_ready"],
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    row.get("evidence_summary") or "",
                    c["oos_reason"],
                    c["recommended_action"],
                    row.get("robustness_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_oos_validation_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT oos_status, count(*) AS rows
                FROM marketcore_ui.edge_oos_validation_v1
                GROUP BY oos_status
                ORDER BY oos_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"oos_status_{row['oos_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_OOS_VALIDATION_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/edge-oos-validation' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/edge-oos-validation":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        oos_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        robustness_status,
                        oos_status,
                        oos_readiness,
                        sample_size_status,
                        pf_status,
                        expectancy_status,
                        winrate_status,
                        pnl_status,
                        robustness_score,
                        oos_required,
                        micro_live_ready,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        oos_reason,
                        recommended_action,
                        source_robustness_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_oos_validation_v1
                    ORDER BY oos_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_oos_validation_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_oos_validation_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/edge_oos_validation.py <<'PY'
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
        return "<p>OOS Validation пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("oos_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(str(row.get("oos_status", "")))}</td>
            <td>{escape(str(row.get("oos_readiness", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("robustness_score"), 4))}</td>
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
                <th>Robustness</th>
                <th>OOS</th>
                <th>Readiness</th>
                <th>Score</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>Trades</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeOosValidationPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-oos-validation",
            title="Edge OOS Validation",
            icon="✓",
            menu_order=19,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-oos-validation?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("oos_status") == "READY_FOR_OOS")
        wait_sample = sum(1 for row in rows if row.get("oos_status") == "WAIT_SAMPLE")
        observe = sum(1 for row in rows if row.get("oos_status") == "OBSERVE_MORE")
        blocked = sum(1 for row in rows if str(row.get("oos_status", "")).startswith("BLOCKED"))

        return f"""
        <section class="card">
            <h2>Edge OOS Validation</h2>
            <p>Out-of-sample readiness проверяет, можно ли кандидата передавать в OOS-контур.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_oos_validation_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready OOS", ctx.formatter.number(ready, 0))}
            {_metric("Observe", ctx.formatter.number(observe, 0))}
            {_metric("Wait Sample", ctx.formatter.number(wait_sample, 0))}
            {_metric("Blocked", ctx.formatter.number(blocked, 0))}
        </div>

        <section class="card">
            <h2>OOS Validation</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_OOS_BACKTEST_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "EdgeOosValidationPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.edge_oos_validation import EdgeOosValidationPage\n",
    )

if "EdgeOosValidationPage()," not in s:
    if "EdgeRobustnessCheckPage()," in s:
        s = s.replace(
            "EdgeRobustnessCheckPage(),",
            "EdgeRobustnessCheckPage(),\n    EdgeOosValidationPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    EdgeOosValidationPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_edge_oos_validation_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_OOS_VALIDATION_V1 ==="

scripts/apply_edge_oos_validation_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_oos_validation_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_oos_validation.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/edge_oos_validation.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/edge_oos_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/edge_oos_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/edge_oos_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > /tmp/edge_oos_robustness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  | tee /tmp/edge_oos_validation_builder_v1.txt

grep -q "VERDICT=EDGE_OOS_VALIDATION_V1_READY" /tmp/edge_oos_validation_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18895 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_edge_oos_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18880 KG_API_BASE_URL=http://127.0.0.1:18895 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/edge_oos_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18895/api/kg/v1/edge-oos-validation?limit=20" \
  > /tmp/edge_oos_validation_api_v1.json

curl -fsS "http://127.0.0.1:18880/edge-oos-validation" \
  > /tmp/edge_oos_validation_page_v1.html

grep -q '"status": "OK"' /tmp/edge_oos_validation_api_v1.json
grep -q '"oos_status"' /tmp/edge_oos_validation_api_v1.json
grep -q '"oos_readiness"' /tmp/edge_oos_validation_api_v1.json
grep -q '"recommended_action"' /tmp/edge_oos_validation_api_v1.json

grep -q "Edge OOS Validation" /tmp/edge_oos_validation_page_v1.html
grep -q "OOS Validation" /tmp/edge_oos_validation_page_v1.html
grep -q "EDGE_OOS_BACKTEST_V1" /tmp/edge_oos_validation_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/edge_oos_validation_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_validation_v1;")
test "$rows" -gt 0

echo "edge_oos_validation_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_OOS_VALIDATION_V1_READY"
echo "VERDICT=TEST_EDGE_OOS_VALIDATION_V1_OK"
SH_TEST

chmod +x scripts/test_edge_oos_validation_v1.sh

scripts/test_edge_oos_validation_v1.sh

echo "VERDICT=BUILD_EDGE_OOS_VALIDATION_V1_OK"
