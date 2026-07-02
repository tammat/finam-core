#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_REAL_DATA_V1 ==="

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-runtime' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-runtime":
                row = fetch_one("""
                    SELECT
                        paper_status,
                        closed_trades_total,
                        closed_trades_today,
                        signals_today,
                        fills_today,
                        signal_fills_today,
                        active_symbols,
                        pnl_today,
                        pnl_total,
                        last_closed_trade_at,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_summary_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {"source": "marketcore_ui.paper_runtime_summary_v1"}))
                return

            if path == "/api/kg/v1/paper-edge-discovery":
                paper = fetch_one("""
                    SELECT
                        paper_status,
                        closed_trades_total,
                        closed_trades_today,
                        signals_today,
                        fills_today,
                        signal_fills_today,
                        active_symbols,
                        pnl_today,
                        pnl_total,
                        last_closed_trade_at,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.paper_runtime_summary_v1
                    WHERE id=1;
                """) or {}

                kg = fetch_one("""
                    SELECT domain, nodes, edges, entity_types, edge_types, last_node_update
                    FROM knowledge_graph.v_api_kg_statistics_v1
                    WHERE domain='PAPER_RUNTIME';
                """) or {}

                validation = fetch_one("""
                    SELECT domain, status, total_findings, finished_at
                    FROM knowledge_graph.v_api_kg_validation_latest_v1
                    WHERE domain='PAPER_RUNTIME';
                """) or {}

                data = {
                    "paper_runtime": paper,
                    "knowledge_graph": kg,
                    "validation": validation,
                    "next_action": "PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1",
                }

                self.send_json(200, response("OK", data, {
                    "source": "kg_api_read_models",
                    "ui_direct_sql": 0,
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
        payload = ctx.api_get("/api/kg/v1/paper-edge-discovery")

        data = payload.get("data") or {}
        paper = data.get("paper_runtime") or {}
        kg = data.get("knowledge_graph") or {}
        validation = data.get("validation") or {}

        paper_status = str(paper.get("paper_status", "UNKNOWN"))
        validation_status = str(validation.get("status", "UNKNOWN"))

        closed_total = ctx.formatter.number(paper.get("closed_trades_total"), 0)
        closed_today = ctx.formatter.number(paper.get("closed_trades_today"), 0)
        signals_today = ctx.formatter.number(paper.get("signals_today"), 0)
        fills_today = ctx.formatter.number(paper.get("fills_today"), 0)
        signal_fills_today = ctx.formatter.number(paper.get("signal_fills_today"), 0)
        active_symbols = ctx.formatter.number(paper.get("active_symbols"), 0)
        pnl_today = ctx.formatter.number(paper.get("pnl_today"), 4)
        pnl_total = ctx.formatter.number(paper.get("pnl_total"), 4)
        last_trade = ctx.formatter.datetime(paper.get("last_closed_trade_at"))
        refreshed_at = ctx.formatter.datetime(paper.get("refreshed_at"))

        kg_nodes = ctx.formatter.number(kg.get("nodes"), 0)
        kg_edges = ctx.formatter.number(kg.get("edges"), 0)
        kg_entity_types = ctx.formatter.number(kg.get("entity_types"), 0)
        kg_edge_types = ctx.formatter.number(kg.get("edge_types"), 0)

        validation_findings = ctx.formatter.number(validation.get("total_findings"), 0)
        validation_finished = ctx.formatter.datetime(validation.get("finished_at"))

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
            {_metric("Signals Today", signals_today, f"Fills: {fills_today}; Signal fills: {signal_fills_today}")}
            {_metric("P&L Total", pnl_total, f"Сегодня: {pnl_today}")}
        </div>

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
                    {_row("Signal fills сегодня", signal_fills_today)}
                    {_row("P&L сегодня", pnl_today)}
                    {_row("P&L всего", pnl_total)}
                    {_row("Последняя закрытая сделка", last_trade)}
                    {_row("Read Model обновлена", refreshed_at)}
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
                    {_row("Типы сущностей", kg_entity_types)}
                    {_row("Типы связей", kg_edge_types)}
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
                    {_row("Завершено", validation_finished)}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>{escape(next_action)}</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperEdgeDiscoveryPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_edge_discovery import PaperEdgeDiscoveryPage\n",
    )

if "PaperEdgeDiscoveryPage()," not in s:
    s = s.replace(
        "HomePage(),",
        "HomePage(),\n    PaperEdgeDiscoveryPage(),",
    )

p.write_text(s)
PY

cat > scripts/test_paper_edge_discovery_real_data_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_REAL_DATA_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_discovery.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

KG_API_HOST=127.0.0.1 KG_API_PORT=18095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_paper_edge_real_data_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18080 KG_API_BASE_URL=http://127.0.0.1:18095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/paper_edge_real_data_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18095/api/kg/v1/paper-runtime" > /tmp/kg_api_paper_runtime_v1.json
curl -fsS "http://127.0.0.1:18095/api/kg/v1/paper-edge-discovery" > /tmp/kg_api_paper_edge_discovery_v1.json
curl -fsS "http://127.0.0.1:18080/paper-edge-discovery" > /tmp/paper_edge_discovery_real_data_v1.html

grep -q '"status": "OK"' /tmp/kg_api_paper_runtime_v1.json
grep -q '"closed_trades_total"' /tmp/kg_api_paper_runtime_v1.json
grep -q '"paper_runtime"' /tmp/kg_api_paper_edge_discovery_v1.json
grep -q '"knowledge_graph"' /tmp/kg_api_paper_edge_discovery_v1.json

grep -q "Центр поиска Edge" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "Paper Runtime Real Data" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "Closed Trades" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "Signals Today" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "P&amp;L Total" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "marketcore_ui.paper_runtime_summary_v1" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "PAPER_RUNTIME" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1" /tmp/paper_edge_discovery_real_data_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_discovery_real_data_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_REAL_DATA_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_REAL_DATA_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_real_data_v1.sh

scripts/test_paper_edge_discovery_real_data_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_REAL_DATA_V1_OK"
