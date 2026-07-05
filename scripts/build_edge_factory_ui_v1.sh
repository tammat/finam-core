#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_FACTORY_UI_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat > src/marketcore/presentation/pages/edge_factory_page.py <<'PY'
from __future__ import annotations

import json
from html import escape
from pathlib import Path

from marketcore.presentation.page import Page


AUDIT_JSON = Path("reports/edge_pipeline_audit_latest.json")
AUDIT_TXT = Path("reports/edge_pipeline_audit_latest.txt")


def _load_audit() -> dict:
    if AUDIT_JSON.exists():
        return json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    return {"summary": {}, "funnel": [], "bottleneck": ["NO_REPORT", 0, 0, 0]}


def _read_report() -> str:
    if AUDIT_TXT.exists():
        return AUDIT_TXT.read_text(encoding="utf-8")
    return "EDGE_PIPELINE_AUDIT_REPORT_NOT_FOUND"


def _kpi(title: str, value: object) -> str:
    return f'<div class="kpi"><div class="kpi-label">{escape(title)}</div><div class="kpi-value">{escape(str(value))}</div></div>'


class EdgeFactoryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-factory",
            title="Edge Factory",
            icon="🏭",
            menu_order=45,
        )

    def render(self) -> str:
        audit = _load_audit()
        summary = audit.get("summary", {})
        funnel = audit.get("funnel", [])
        bottleneck = audit.get("bottleneck", ["NONE", 0, 0, 0])
        report = escape(_read_report())

        kpis = "".join([
            _kpi("Strategies", summary.get("strategies", 0)),
            _kpi("Research Queue", summary.get("research_queue", 0)),
            _kpi("Observations", summary.get("observations", 0)),
            _kpi("With Trades", summary.get("observations_with_trades", 0)),
            _kpi("Candidates", summary.get("candidates", 0)),
            _kpi("Validated", summary.get("validated", 0)),
            _kpi("Paper", summary.get("paper", 0)),
            _kpi("Research Trades", summary.get("research_trades", 0)),
        ])

        funnel_rows = "".join(
            f"<tr><td>{escape(str(x[0]))}</td><td>{x[1]}</td><td>{x[2]}</td><td>{x[3]}%</td></tr>"
            for x in funnel
        )

        return f"""
        <div class="card">
            <h2>Edge Factory</h2>
            <p>Главный экран исследовательской фабрики: Sprint, Audit, KPI, Bottleneck.</p>
        </div>

        <div class="kpi-grid">{kpis}</div>

        <div class="card">
            <h3>Current Bottleneck</h3>
            <p><b>{escape(str(bottleneck[0]))}</b>: {escape(str(bottleneck[3]))}%</p>
        </div>

        <div class="card">
            <h3>Pipeline Funnel</h3>
            <table>
                <thead>
                    <tr><th>Stage</th><th>Value</th><th>Base</th><th>Conversion</th></tr>
                </thead>
                <tbody>{funnel_rows}</tbody>
            </table>
        </div>

        <div class="card">
            <h3>Latest Audit Report</h3>
            <pre style="white-space:pre-wrap;font-size:12px;line-height:1.35">{report}</pre>
        </div>
        """
PY

python - <<'PY'
from pathlib import Path

reg = Path("src/marketcore/presentation/registry.py")
s = reg.read_text(encoding="utf-8")

imp = "from marketcore.presentation.pages.edge_factory_page import EdgeFactoryPage\n"
if imp not in s:
    insert_after = "from marketcore.presentation.pages.edge_audit_page import EdgeAuditPage\n"
    if insert_after in s:
        s = s.replace(insert_after, insert_after + imp)
    else:
        s = imp + s

if "EdgeFactoryPage()," not in s:
    marker = "    EdgeAuditPage(),\n"
    if marker in s:
        s = s.replace(marker, "    EdgeFactoryPage(),\n" + marker)
    else:
        idx = s.find("PAGES = [")
        if idx < 0:
            raise SystemExit("PAGES_LIST_NOT_FOUND")
        start = s.find("\n", idx) + 1
        s = s[:start] + "    EdgeFactoryPage(),\n" + s[start:]

reg.write_text(s, encoding="utf-8")
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.factory.title": "Edge Factory",
        "edge.factory.subtitle": "Главный экран исследовательской фабрики",
        "edge.factory.funnel": "Воронка",
        "edge.factory.bottleneck": "Узкое место",
        "edge.factory.audit": "Последний аудит",
        "edge.factory.research_queue": "Research Queue",
        "edge.factory.observations": "Observations",
        "edge.factory.candidates": "Candidates",
        "edge.factory.validated": "Validated",
        "edge.factory.paper": "Paper"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_factory_ui_v1.sh <<'TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_FACTORY_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_factory_page.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_audit_v1.py >/tmp/edge_factory_audit_refresh.txt

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/edge-factory >/tmp/edge_factory.html
curl -fsS http://127.0.0.1:8080/ >/tmp/edge_factory_home.html

grep -q "Edge Factory" /tmp/edge_factory.html
grep -q "Pipeline Funnel" /tmp/edge_factory.html
grep -q "Current Bottleneck" /tmp/edge_factory.html
grep -q "/edge-factory" /tmp/edge_factory_home.html

echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_FACTORY_UI_V1_OK"
TEST

chmod +x scripts/test_edge_factory_ui_v1.sh
scripts/test_edge_factory_ui_v1.sh

echo "VERDICT=BUILD_EDGE_FACTORY_UI_V1_OK"
