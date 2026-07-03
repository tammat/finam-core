#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_ROBUSTNESS_CHECK_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/014_edge_robustness_check_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_robustness_check_v1 (
    robustness_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    pipeline_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',

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
    weakness_summary TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_pipeline_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_ROBUSTNESS_CHECK_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_robustness_check_v1 TO alex;

COMMIT;

SELECT 'EDGE_ROBUSTNESS_CHECK_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_edge_robustness_check_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/014_edge_robustness_check_v1.sql
SH_APPLY

chmod +x scripts/apply_edge_robustness_check_v1.sh

cat > src/scripts/build_edge_robustness_check_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_ROBUSTNESS_CHECK_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def normalize_winrate(value) -> Decimal:
    wr = dec(value)
    if wr > Decimal("1"):
        return wr / Decimal("100")
    return wr


def classify(row: dict) -> dict:
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))
    winrate = normalize_winrate(row.get("winrate"))
    net_pnl = dec(row.get("net_pnl"))

    sample_size_status = "PASS" if trades >= 30 else "WAIT_SAMPLE"

    if pf >= Decimal("1.2"):
        pf_status = "PASS"
    elif pf >= Decimal("1.0"):
        pf_status = "WATCH"
    else:
        pf_status = "FAIL"

    if expectancy > Decimal("0"):
        expectancy_status = "PASS"
    elif expectancy == Decimal("0"):
        expectancy_status = "WATCH"
    else:
        expectancy_status = "FAIL"

    if winrate >= Decimal("0.50"):
        winrate_status = "PASS"
    elif winrate >= Decimal("0.45"):
        winrate_status = "WATCH"
    else:
        winrate_status = "FAIL"

    pnl_status = "PASS" if net_pnl > Decimal("0") else "FAIL"

    sample_score = Decimal("1") if sample_size_status == "PASS" else Decimal("0")
    pf_score = Decimal("1") if pf_status == "PASS" else Decimal("0.5") if pf_status == "WATCH" else Decimal("0")
    exp_score = Decimal("1") if expectancy_status == "PASS" else Decimal("0.5") if expectancy_status == "WATCH" else Decimal("0")
    wr_score = Decimal("1") if winrate_status == "PASS" else Decimal("0.5") if winrate_status == "WATCH" else Decimal("0")
    pnl_score = Decimal("1") if pnl_status == "PASS" else Decimal("0")

    robustness_score = (
        sample_score * Decimal("0.25")
        + pf_score * Decimal("0.25")
        + exp_score * Decimal("0.25")
        + wr_score * Decimal("0.15")
        + pnl_score * Decimal("0.10")
    )

    if trades < 30:
        robustness_status = "WAIT_SAMPLE"
        recommended_action = "Накопить выборку Paper Runtime до 30+ сделок."
        weakness_summary = "Недостаточная выборка для robustness-проверки."
        oos_required = False
    elif pf >= Decimal("1.2") and expectancy > Decimal("0") and winrate >= Decimal("0.45"):
        robustness_status = "ROBUSTNESS_REQUIRED"
        recommended_action = "Запустить robustness-проверку по времени, режимам рынка и параметрам."
        weakness_summary = "До продвижения требуется проверить устойчивость и OOS."
        oos_required = True
    elif pf >= Decimal("1.0") and expectancy >= Decimal("0"):
        robustness_status = "WATCHLIST"
        recommended_action = "Продолжить наблюдение и проверить устойчивость после накопления новых сделок."
        weakness_summary = "Преимущество слабое или недостаточно устойчивое."
        oos_required = False
    else:
        robustness_status = "ROBUSTNESS_REJECT"
        recommended_action = "Не продвигать кандидата без улучшения статистики."
        weakness_summary = "Статистика не подтверждает устойчивый edge."
        oos_required = False

    evidence_summary = (
        f"Trades={trades}; "
        f"PF={pf}; "
        f"Expectancy={expectancy}; "
        f"WinRate={winrate}; "
        f"NetPnL={net_pnl}; "
        f"Score={row.get('score') or 0}"
    )

    return {
        "sample_size_status": sample_size_status,
        "pf_status": pf_status,
        "expectancy_status": expectancy_status,
        "winrate_status": winrate_status,
        "pnl_status": pnl_status,
        "robustness_status": robustness_status,
        "robustness_score": robustness_score,
        "oos_required": oos_required,
        "micro_live_ready": False,
        "evidence_summary": evidence_summary,
        "weakness_summary": weakness_summary,
        "recommended_action": recommended_action,
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_ROBUSTNESS_CHECK_V1 ===")

            cur.execute("""
                SELECT
                    pipeline_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    pipeline_status,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    evidence_summary,
                    risk_notes
                FROM marketcore_ui.edge_validation_pipeline_v1
                ORDER BY
                    CASE
                        WHEN pipeline_status='READY_FOR_ROBUSTNESS' THEN 1
                        WHEN pipeline_status='OBSERVE_MORE' THEN 2
                        WHEN pipeline_status='ACCUMULATE_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    pipeline_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_robustness_check_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row)

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_robustness_check_v1 (
                        robustness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        pipeline_status,
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
                        recommended_action,
                        source_pipeline_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,
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
                    row.get("pipeline_status") or "UNKNOWN",
                    c["robustness_status"],
                    c["sample_size_status"],
                    c["pf_status"],
                    c["expectancy_status"],
                    c["winrate_status"],
                    c["pnl_status"],
                    c["robustness_score"],
                    c["oos_required"],
                    c["micro_live_ready"],
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    c["evidence_summary"],
                    c["weakness_summary"],
                    c["recommended_action"],
                    row.get("pipeline_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_robustness_check_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT robustness_status, count(*) AS rows
                FROM marketcore_ui.edge_robustness_check_v1
                GROUP BY robustness_status
                ORDER BY robustness_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"robustness_status_{row['robustness_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/edge-robustness-check' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/edge-robustness-check":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        robustness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        pipeline_status,
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
                        recommended_action,
                        source_pipeline_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_robustness_check_v1
                    ORDER BY robustness_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_robustness_check_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_robustness_check_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/edge_robustness_check.py <<'PY'
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
        return "<p>Robustness Check пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("robustness_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(str(row.get("sample_size_status", "")))}</td>
            <td>{escape(str(row.get("pf_status", "")))}</td>
            <td>{escape(str(row.get("expectancy_status", "")))}</td>
            <td>{escape(str(row.get("winrate_status", "")))}</td>
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
                <th>Sample</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>WinRate</th>
                <th>Score</th>
                <th>PF</th>
                <th>Exp.</th>
                <th>Trades</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeRobustnessCheckPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-robustness-check",
            title="Edge Robustness Check",
            icon="◇",
            menu_order=18,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-robustness-check?limit=50")
        rows = payload.get("data") or []

        wait_sample = sum(1 for row in rows if row.get("robustness_status") == "WAIT_SAMPLE")
        required = sum(1 for row in rows if row.get("robustness_status") == "ROBUSTNESS_REQUIRED")
        watchlist = sum(1 for row in rows if row.get("robustness_status") == "WATCHLIST")
        rejected = sum(1 for row in rows if row.get("robustness_status") == "ROBUSTNESS_REJECT")

        return f"""
        <section class="card">
            <h2>Edge Robustness Check</h2>
            <p>Проверка устойчивости кандидатов перед OOS и последующим продвижением.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_robustness_check_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Required", ctx.formatter.number(required, 0), "Готовы к robustness")}
            {_metric("Watchlist", ctx.formatter.number(watchlist, 0), "Наблюдать")}
            {_metric("Wait Sample", ctx.formatter.number(wait_sample, 0), "Копить выборку")}
            {_metric("Rejected", ctx.formatter.number(rejected, 0), "Не продвигать")}
        </div>

        <section class="card">
            <h2>Robustness Check</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_OOS_VALIDATION_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "EdgeRobustnessCheckPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.edge_robustness_check import EdgeRobustnessCheckPage\n",
    )

if "EdgeRobustnessCheckPage()," not in s:
    if "EdgeValidationPipelinePage()," in s:
        s = s.replace(
            "EdgeValidationPipelinePage(),",
            "EdgeValidationPipelinePage(),\n    EdgeRobustnessCheckPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    EdgeRobustnessCheckPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_edge_robustness_check_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_ROBUSTNESS_CHECK_V1 ==="

scripts/apply_edge_robustness_check_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_robustness_check_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_robustness_check.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/edge_robustness_check.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/edge_robustness_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/edge_robustness_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/edge_robustness_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  | tee /tmp/edge_robustness_builder_v1.txt

grep -q "VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY" /tmp/edge_robustness_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18795 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_edge_robustness_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18780 KG_API_BASE_URL=http://127.0.0.1:18795 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/edge_robustness_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18795/api/kg/v1/edge-robustness-check?limit=20" \
  > /tmp/edge_robustness_api_v1.json

curl -fsS "http://127.0.0.1:18780/edge-robustness-check" \
  > /tmp/edge_robustness_page_v1.html

grep -q '"status": "OK"' /tmp/edge_robustness_api_v1.json
grep -q '"robustness_status"' /tmp/edge_robustness_api_v1.json
grep -q '"robustness_score"' /tmp/edge_robustness_api_v1.json
grep -q '"recommended_action"' /tmp/edge_robustness_api_v1.json

grep -q "Edge Robustness Check" /tmp/edge_robustness_page_v1.html
grep -q "Robustness Check" /tmp/edge_robustness_page_v1.html
grep -q "EDGE_OOS_VALIDATION_V1" /tmp/edge_robustness_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/edge_robustness_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_robustness_check_v1;")
test "$rows" -gt 0

echo "edge_robustness_check_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY"
echo "VERDICT=TEST_EDGE_ROBUSTNESS_CHECK_V1_OK"
SH_TEST

chmod +x scripts/test_edge_robustness_check_v1.sh

scripts/test_edge_robustness_check_v1.sh

echo "VERDICT=BUILD_EDGE_ROBUSTNESS_CHECK_V1_OK"
