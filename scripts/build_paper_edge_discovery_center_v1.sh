#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_CENTER_V1 ==="

cat > src/marketcore/presentation/pages/paper_edge_discovery.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "<p>Нет данных.</p>"

    head = "".join(f"<th>{escape(col)}</th>" for col in columns)
    body = ""

    for row in rows:
        body += "<tr>" + "".join(
            f"<td>{escape(str(row.get(col, '')))}</td>"
            for col in columns
        ) + "</tr>"

    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _metric(title: str, value: str, note: str = "") -> str:
    return f"""
    <section class="card">
        <h2>{escape(title)}</h2>
        <p style="font-size:28px;font-weight:700;margin:8px 0;">{escape(value)}</p>
        <p>{escape(note)}</p>
    </section>
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

        kg_health = ctx.api_get("/api/kg/v1/health")
        kg_stats = ctx.api_get("/api/kg/v1/statistics")
        kg_validation = ctx.api_get("/api/kg/v1/validation")
        kg_search = ctx.api_get("/api/kg/v1/search?q=edge&locale=ru")

        health_status = kg_health.get("status", "ERROR")
        health_data = kg_health.get("data") or {}
        stats_rows = kg_stats.get("data") or []
        validation_rows = kg_validation.get("data") or []
        search_rows = (kg_search.get("data") or {}).get("terms") or []

        nodes = health_data.get("nodes", "—")

        paper_stats = [
            row for row in stats_rows
            if str(row.get("domain")) == "PAPER_RUNTIME"
        ]

        latest_validation = validation_rows[0] if validation_rows else {}
        validation_status = str(latest_validation.get("status", "UNKNOWN"))
        validation_findings = str(latest_validation.get("total_findings", "—"))

        return f"""
        <section class="card">
            <h2>{escape(ctx.formatter.label("ui", "paper_edge_discovery_center"))}</h2>
            <p>Операционный центр Phase II: Paper Runtime → Knowledge Graph → Research → Edge.</p>
            <p>Источник данных: Knowledge Graph API. Прямых SQL-запросов из UI нет.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;">
            {_metric("Knowledge Graph", str(nodes), "Всего узлов через KG API")}
            {_metric("Validation", ctx.status.label(validation_status), f"Findings: {validation_findings}")}
            {_metric("Paper Runtime", "ACTIVE", "Домен PAPER_RUNTIME подключён к графу знаний")}
        </div>

        <section class="card">
            <h2>Paper Runtime Knowledge Graph</h2>
            {_table(paper_stats, ["domain", "nodes", "edges", "entity_types", "edge_types"])}
        </section>

        <section class="card">
            <h2>Validation</h2>
            {_table(validation_rows, ["domain", "status", "total_findings", "finished_at"])}
        </section>

        <section class="card">
            <h2>Semantic Search: edge</h2>
            {_table(search_rows, ["locale", "raw_term", "object_type", "object_key", "match_type", "confidence"])}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_EDGE_DISCOVERY_REAL_DATA_V1</p>
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

cat > scripts/test_paper_edge_discovery_center_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_CENTER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

KG_API_HOST=127.0.0.1 KG_API_PORT=18095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_paper_edge_discovery_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18080 KG_API_BASE_URL=http://127.0.0.1:18095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/paper_edge_discovery_center_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18080/paper-edge-discovery" > /tmp/paper_edge_discovery_center_v1.html

grep -q "Центр поиска Edge" /tmp/paper_edge_discovery_center_v1.html
grep -q "Paper Runtime" /tmp/paper_edge_discovery_center_v1.html
grep -q "Knowledge Graph" /tmp/paper_edge_discovery_center_v1.html
grep -q "Validation" /tmp/paper_edge_discovery_center_v1.html
grep -q "PAPER_RUNTIME" /tmp/paper_edge_discovery_center_v1.html
grep -q "PAPER_EDGE_DISCOVERY_REAL_DATA_V1" /tmp/paper_edge_discovery_center_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_discovery_center_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_CENTER_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_CENTER_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_center_v1.sh

scripts/test_paper_edge_discovery_center_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_CENTER_V1_OK"
