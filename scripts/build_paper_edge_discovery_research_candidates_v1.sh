#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts

cat > sql/marketcore_ui/011_paper_edge_research_candidates_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_research_candidates_v1 (
    candidate_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',
    candidate_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    expectancy NUMERIC(20,6),
    profit_factor NUMERIC(20,6),
    winrate NUMERIC(20,6),
    trades INTEGER,
    net_pnl NUMERIC(20,6),
    score NUMERIC(20,6),
    source_table TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_research_candidates_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_edge_discovery_research_candidates_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/011_paper_edge_research_candidates_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_edge_discovery_research_candidates_v1.sh

cat > src/scripts/build_paper_edge_discovery_research_candidates_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal, InvalidOperation

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1"

SOURCE_TABLES = [
    "public.analytics_global_edge_expanded_runtime_candidates_v2",
    "public.analytics_global_edge_runtime_candidates_v2",
    "public.analytics_global_edge_top3_runtime_approval_board_v1",
]


def table_exists(cur, full_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s);", (full_name,))
    row = cur.fetchone()
    if row is None:
        return False
    if isinstance(row, dict):
        return next(iter(row.values())) is not None
    return row[0] is not None


def pick(row: dict, keys: list[str], default=None):
    for key in keys:
        if key in row and row[key] is not None:
            value = row[key]
            if isinstance(value, str) and value.strip() == "":
                continue
            return value
    return default


def as_text(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def as_decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def as_int(value):
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def candidate_score(candidate: dict) -> tuple:
    score = candidate.get("score")
    pf = candidate.get("profit_factor")
    expectancy = candidate.get("expectancy")
    net_pnl = candidate.get("net_pnl")
    trades = candidate.get("trades")

    def n(value):
        return float(value) if value is not None else -10**18

    return (
        n(score),
        n(pf),
        n(expectancy),
        n(net_pnl),
        n(trades),
    )


def load_candidates_from_table(cur, full_name: str) -> list[dict]:
    cur.execute(f"SELECT * FROM {full_name} LIMIT 2000;")
    rows = [dict(row) for row in cur.fetchall()]

    candidates: list[dict] = []

    for row in rows:
        symbol = as_text(pick(row, ["symbol", "ticker", "instrument", "secid"], ""))
        strategy = as_text(pick(row, ["strategy", "strategy_name", "model", "edge_name"], ""))
        timeframe = as_text(pick(row, ["timeframe", "tf", "horizon"], ""))
        side = as_text(pick(row, ["side", "direction"], ""))

        status = as_text(
            pick(
                row,
                ["candidate_status", "status", "board_decision", "decision", "verdict"],
                "CANDIDATE",
            ),
            "CANDIDATE",
        )

        expectancy = as_decimal(
            pick(row, ["expectancy", "expectancy_points", "avg_pnl", "mean_pnl"])
        )
        profit_factor = as_decimal(
            pick(row, ["profit_factor", "pf"])
        )
        winrate = as_decimal(
            pick(row, ["winrate", "win_rate", "win_rate_pct"])
        )
        trades = as_int(
            pick(row, ["closed_cycles", "closed_trades", "trades", "sample_size", "n_trades"])
        )
        net_pnl = as_decimal(
            pick(row, ["net_pnl", "pnl", "total_pnl", "gross_pnl"])
        )
        score = as_decimal(
            pick(row, ["edge_score", "score", "candidate_score", "top_score", "quality_score"])
        )

        if not symbol and not strategy:
            continue

        candidates.append(
            {
                "symbol": symbol,
                "strategy": strategy,
                "timeframe": timeframe,
                "side": side,
                "candidate_status": status,
                "expectancy": expectancy,
                "profit_factor": profit_factor,
                "winrate": winrate,
                "trades": trades,
                "net_pnl": net_pnl,
                "score": score,
                "source_table": full_name,
            }
        )

    candidates.sort(key=candidate_score, reverse=True)
    return candidates[:20]


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1 ===")

            selected_source = "NONE"
            candidates: list[dict] = []

            for source_table in SOURCE_TABLES:
                if not table_exists(cur, source_table):
                    print(f"source_table={source_table} exists=0 rows=0")
                    continue

                table_candidates = load_candidates_from_table(cur, source_table)
                print(f"source_table={source_table} exists=1 candidates={len(table_candidates)}")

                if table_candidates:
                    selected_source = source_table
                    candidates = table_candidates
                    break

            cur.execute("DELETE FROM marketcore_ui.paper_edge_research_candidates_v1;")

            for idx, candidate in enumerate(candidates, start=1):
                cur.execute(
                    """
                    INSERT INTO marketcore_ui.paper_edge_research_candidates_v1 (
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
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                    """,
                    (
                        idx,
                        candidate["symbol"],
                        candidate["strategy"],
                        candidate["timeframe"],
                        candidate["side"],
                        candidate["candidate_status"],
                        candidate["expectancy"],
                        candidate["profit_factor"],
                        candidate["winrate"],
                        candidate["trades"],
                        candidate["net_pnl"],
                        candidate["score"],
                        candidate["source_table"],
                        SOURCE_VERSION,
                        build_id,
                    ),
                )

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_edge_research_candidates_v1;")
            rows_written = int(cur.fetchone()["rows"])

    print(f"selected_source={selected_source}")
    print(f"rows_written={rows_written}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-edge-research-candidates' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-edge-research-candidates":
                limit = int(q.get("limit", ["20"])[0])
                rows = fetch_all("""
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
                    ORDER BY candidate_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_research_candidates_v1",
                    "ui_direct_sql": 0
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_edge_discovery.py <<'PY'
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


def _candidate_table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Кандидаты Research пока не найдены.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("candidate_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("side", "")))}</td>
            <td>{escape(str(row.get("candidate_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.percent(row.get("winrate"), 2))}</td>
            <td>{escape(ctx.formatter.number(row.get("trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("net_pnl"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("score"), 4))}</td>
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
                <th>Side</th>
                <th>Статус</th>
                <th>Expectancy</th>
                <th>PF</th>
                <th>WinRate</th>
                <th>Trades</th>
                <th>Net PnL</th>
                <th>Score</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeDiscoveryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-discovery",
            title="Paper Edge Discovery",
            icon="◇",
            menu_order=15,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        discovery = ctx.api_get("/api/kg/v1/paper-edge-discovery")
        candidates_payload = ctx.api_get("/api/kg/v1/paper-edge-research-candidates?limit=20")

        data = discovery.get("data") or {}
        paper = data.get("paper_runtime") or {}
        kg = data.get("knowledge_graph") or {}
        validation = data.get("validation") or {}
        candidates = candidates_payload.get("data") or []

        paper_status = str(paper.get("paper_status", "UNKNOWN"))
        validation_status = str(validation.get("status", "UNKNOWN"))

        closed_total = ctx.formatter.number(paper.get("closed_trades_total"), 0)
        closed_today = ctx.formatter.number(paper.get("closed_trades_today"), 0)
        signals_today = ctx.formatter.number(paper.get("signals_today"), 0)
        fills_today = ctx.formatter.number(paper.get("fills_today"), 0)
        pnl_today = ctx.formatter.number(paper.get("pnl_today"), 4)
        pnl_total = ctx.formatter.number(paper.get("pnl_total"), 4)
        active_symbols = ctx.formatter.number(paper.get("active_symbols"), 0)

        kg_nodes = ctx.formatter.number(kg.get("nodes"), 0)
        kg_edges = ctx.formatter.number(kg.get("edges"), 0)
        validation_findings = ctx.formatter.number(validation.get("total_findings"), 0)

        next_action = str(data.get("next_action", "PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1"))

        return f"""
        <section class="card">
            <h2>{escape(ctx.formatter.label("ui", "paper_edge_discovery_center"))}</h2>
            <p>Операционный центр Phase II: Paper Runtime → Knowledge Graph → Research → Edge.</p>
            <p>Источник данных: Knowledge Graph API. Прямых SQL-запросов из UI нет.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            {_metric("Paper Runtime", ctx.status.label(paper_status), "Реальные данные paper-контура")}
            {_metric("Closed Trades", closed_total, f"Сегодня: {closed_today}")}
            {_metric("Signals Today", signals_today, f"Fills: {fills_today}")}
            {_metric("P&L Total", pnl_total, f"Сегодня: {pnl_today}")}
        </div>

        <section class="card">
            <h2>Research Candidates</h2>
            <p>Источник: marketcore_ui.paper_edge_research_candidates_v1</p>
            {_candidate_table(candidates, ctx)}
        </section>

        <section class="card">
            <h2>Paper Runtime Real Data</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Активные инструменты", active_symbols)}
                    {_row("Закрытые сделки всего", closed_total)}
                    {_row("Закрытые сделки сегодня", closed_today)}
                    {_row("Сигналы сегодня", signals_today)}
                    {_row("Исполнения сегодня", fills_today)}
                    {_row("P&L сегодня", pnl_today)}
                    {_row("P&L всего", pnl_total)}
                    {_row("Источник", "marketcore_ui.paper_runtime_summary_v1")}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Knowledge Graph</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Домен", str(kg.get("domain", "PAPER_RUNTIME")))}
                    {_row("Узлы", kg_nodes)}
                    {_row("Связи", kg_edges)}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Validation</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Статус", ctx.status.label(validation_status))}
                    {_row("Findings", validation_findings)}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>{escape(next_action)}</p>
        </section>
        """
PY

cat > scripts/test_paper_edge_discovery_research_candidates_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1 ==="

scripts/apply_paper_edge_discovery_research_candidates_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/app.py

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  | tee /tmp/paper_edge_research_candidates_build_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY" \
  /tmp/paper_edge_research_candidates_build_v1.txt

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_discovery.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

KG_API_HOST=127.0.0.1 KG_API_PORT=18195 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_candidates_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18180 KG_API_BASE_URL=http://127.0.0.1:18195 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/paper_edge_candidates_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18195/api/kg/v1/paper-edge-research-candidates" \
  > /tmp/paper_edge_research_candidates_api_v1.json

curl -fsS "http://127.0.0.1:18180/paper-edge-discovery" \
  > /tmp/paper_edge_research_candidates_page_v1.html

grep -q '"status": "OK"' /tmp/paper_edge_research_candidates_api_v1.json
grep -q "Research Candidates" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "marketcore_ui.paper_edge_research_candidates_v1" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "Paper Runtime Real Data" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "PAPER_RUNTIME" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_research_candidates_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")

echo "research_candidates_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_research_candidates_v1.sh

scripts/test_paper_edge_discovery_research_candidates_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_OK"
