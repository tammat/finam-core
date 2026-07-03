#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_SAMPLE_ACCUMULATION_MONITOR_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/018_paper_sample_accumulation_monitor_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_sample_accumulation_monitor_v1 (
    monitor_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

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

    sample_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,

    micro_live_ready BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    block_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_readiness_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_SAMPLE_ACCUMULATION_MONITOR_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_sample_accumulation_monitor_v1 TO alex;

COMMIT;

SELECT 'PAPER_SAMPLE_ACCUMULATION_MONITOR_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_sample_accumulation_monitor_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/018_paper_sample_accumulation_monitor_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_sample_accumulation_monitor_v1.sh

cat > src/scripts/build_paper_sample_accumulation_monitor_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_SAMPLE_ACCUMULATION_MONITOR_V1"
REQUIRED_TOTAL_TRADES = 30
REQUIRED_OOS_TRADES = 10


def progress(total_trades: int, oos_trades: int) -> Decimal:
    total_part = min(total_trades, REQUIRED_TOTAL_TRADES) / REQUIRED_TOTAL_TRADES
    oos_part = min(oos_trades, REQUIRED_OOS_TRADES) / REQUIRED_OOS_TRADES
    return Decimal(str(round((total_part * 0.70 + oos_part * 0.30) * 100, 2)))


def classify(total_trades: int, oos_trades: int) -> tuple[str, str]:
    remaining_total = max(REQUIRED_TOTAL_TRADES - total_trades, 0)
    remaining_oos = max(REQUIRED_OOS_TRADES - oos_trades, 0)

    if remaining_total == 0 and remaining_oos == 0:
        return "SAMPLE_READY", "Выборка достаточна. Можно продолжать Micro Live readiness / risk review."

    if remaining_total > 0 and remaining_oos > 0:
        return "WAIT_BOTH_SAMPLE", "Продолжить Paper Runtime: не хватает общей и OOS-выборки."

    if remaining_total > 0:
        return "WAIT_TOTAL_SAMPLE", "Продолжить Paper Runtime: не хватает общей выборки."

    return "WAIT_OOS_SAMPLE", "Продолжить OOS-наблюдение: не хватает OOS-сделок."


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_SAMPLE_ACCUMULATION_MONITOR_V1 ===")

            cur.execute("""
                SELECT
                    readiness_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    readiness_status,
                    backtest_status,
                    oos_status,
                    robustness_status,
                    total_trades,
                    oos_trades,
                    micro_live_ready,
                    micro_live_allowed,
                    block_reason,
                    recommended_action
                FROM marketcore_ui.micro_live_readiness_v1
                ORDER BY
                    CASE
                        WHEN readiness_status IN ('WAIT_SAMPLE','WAIT_OOS_SAMPLE') THEN 1
                        WHEN readiness_status LIKE 'BLOCKED%' THEN 2
                        WHEN readiness_status='READY_FOR_RISK_REVIEW' THEN 3
                        ELSE 4
                    END,
                    readiness_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")

            for idx, row in enumerate(rows, start=1):
                total_trades = int(row.get("total_trades") or 0)
                oos_trades = int(row.get("oos_trades") or 0)

                remaining_total = max(REQUIRED_TOTAL_TRADES - total_trades, 0)
                remaining_oos = max(REQUIRED_OOS_TRADES - oos_trades, 0)

                sample_status, sample_action = classify(total_trades, oos_trades)

                recommended_action = sample_action
                if row.get("recommended_action"):
                    recommended_action = f"{sample_action} Previous gate: {row.get('recommended_action')}"

                cur.execute("""
                    INSERT INTO marketcore_ui.paper_sample_accumulation_monitor_v1 (
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
                        block_reason,
                        recommended_action,
                        source_readiness_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("readiness_status") or "UNKNOWN",
                    row.get("backtest_status") or "UNKNOWN",
                    row.get("oos_status") or "UNKNOWN",
                    row.get("robustness_status") or "UNKNOWN",
                    total_trades,
                    REQUIRED_TOTAL_TRADES,
                    remaining_total,
                    oos_trades,
                    REQUIRED_OOS_TRADES,
                    remaining_oos,
                    sample_status,
                    progress(total_trades, oos_trades),
                    bool(row.get("micro_live_ready") or False),
                    bool(row.get("micro_live_allowed") or False),
                    row.get("block_reason") or "",
                    recommended_action,
                    row.get("readiness_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT sample_status, count(*) AS rows
                FROM marketcore_ui.paper_sample_accumulation_monitor_v1
                GROUP BY sample_status
                ORDER BY sample_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"sample_status_{row['sample_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-sample-accumulation-monitor' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-sample-accumulation-monitor":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
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
                        block_reason,
                        recommended_action,
                        source_readiness_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_sample_accumulation_monitor_v1
                    ORDER BY monitor_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_sample_accumulation_monitor_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_sample_accumulation_monitor_v1",
                    "orders_changed": 0,
                    "execution_changed": 0
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
        payload = ctx.api_get("/api/kg/v1/paper-sample-accumulation-monitor?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("sample_status") == "SAMPLE_READY")
        wait_both = sum(1 for row in rows if row.get("sample_status") == "WAIT_BOTH_SAMPLE")
        wait_total = sum(1 for row in rows if row.get("sample_status") == "WAIT_TOTAL_SAMPLE")
        wait_oos = sum(1 for row in rows if row.get("sample_status") == "WAIT_OOS_SAMPLE")

        return f"""
        <section class="card">
            <h2>Paper Sample Accumulation Monitor</h2>
            <p>Монитор показывает, сколько paper-сделок и OOS-сделок осталось накопить до Micro Live readiness.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_sample_accumulation_monitor_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready", ctx.formatter.number(ready, 0))}
            {_metric("Wait Both", ctx.formatter.number(wait_both, 0))}
            {_metric("Wait Total", ctx.formatter.number(wait_total, 0))}
            {_metric("Wait OOS", ctx.formatter.number(wait_oos, 0))}
        </div>

        <section class="card">
            <h2>Accumulation</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_V1</p>
        </section>
        """
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

cat > scripts/test_paper_sample_accumulation_monitor_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_SAMPLE_ACCUMULATION_MONITOR_V1 ==="

scripts/apply_paper_sample_accumulation_monitor_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_sample_accumulation_monitor_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/sample_monitor_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/sample_monitor_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/sample_monitor_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > /tmp/sample_monitor_robustness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > /tmp/sample_monitor_oos_validation_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  > /tmp/sample_monitor_oos_backtest_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_micro_live_readiness_v1.py \
  > /tmp/sample_monitor_micro_live_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_sample_accumulation_monitor_v1.py \
  | tee /tmp/paper_sample_accumulation_monitor_builder_v1.txt

grep -q "VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY" /tmp/paper_sample_accumulation_monitor_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19295 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_sample_monitor_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19280 KG_API_BASE_URL=http://127.0.0.1:19295 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/sample_monitor_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19295/api/kg/v1/paper-sample-accumulation-monitor?limit=20" \
  > /tmp/paper_sample_accumulation_monitor_api_v1.json

curl -fsS "http://127.0.0.1:19280/paper-sample-accumulation-monitor" \
  > /tmp/paper_sample_accumulation_monitor_page_v1.html

grep -q '"status": "OK"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"sample_status"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"remaining_total_trades"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"remaining_oos_trades"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"progress_pct"' /tmp/paper_sample_accumulation_monitor_api_v1.json

grep -q "Paper Sample Accumulation Monitor" /tmp/paper_sample_accumulation_monitor_page_v1.html
grep -q "Accumulation" /tmp/paper_sample_accumulation_monitor_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_V1" /tmp/paper_sample_accumulation_monitor_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_sample_accumulation_monitor_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1 WHERE micro_live_allowed=true;")

test "$rows" -gt 0
test "$allowed" = "0"

echo "paper_sample_accumulation_monitor_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY"
echo "VERDICT=TEST_PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_OK"
SH_TEST

chmod +x scripts/test_paper_sample_accumulation_monitor_v1.sh

scripts/test_paper_sample_accumulation_monitor_v1.sh

echo "VERDICT=BUILD_PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_OK"
