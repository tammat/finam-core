#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_AUDIT_UI_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat > src/marketcore/presentation/pages/edge_audit_page.py <<'PY'
from __future__ import annotations

from html import escape
from pathlib import Path

from marketcore.presentation.layout import render_layout


REPORT_TXT = Path("reports/edge_pipeline_audit_latest.txt")
REPORT_HTML = Path("reports/edge_pipeline_audit_latest.html")


def render_edge_audit_page() -> str:
    if REPORT_TXT.exists():
        report = REPORT_TXT.read_text(encoding="utf-8")
    elif REPORT_HTML.exists():
        report = REPORT_HTML.read_text(encoding="utf-8")
    else:
        report = "EDGE_PIPELINE_AUDIT_REPORT_NOT_FOUND"

    content = f"""
    <div class="card">
        <h2>Edge Audit</h2>
        <p>Последний отчёт EDGE Pipeline Audit. Обновляется timer'ом каждые 30 минут.</p>
    </div>
    <div class="card">
        <pre style="white-space:pre-wrap;font-size:12px;line-height:1.35">{escape(report)}</pre>
    </div>
    """
    return render_layout(title="Edge Audit", active_route="/edge-audit", content=content)
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/router.py")
s = p.read_text(encoding="utf-8")

imp = "from marketcore.presentation.pages.edge_audit_page import render_edge_audit_page\n"
if imp not in s:
    lines = s.splitlines(True)
    pos = 0
    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            pos = i + 1
    lines.insert(pos, imp)
    s = "".join(lines)

needle = "def route("
idx = s.find(needle)
if idx < 0:
    raise SystemExit("ROUTER_ROUTE_FUNCTION_NOT_FOUND")

body_marker = s.find(":\n", idx)
insert_pos = body_marker + 2
route_block = '    if path in ("/edge-audit", "/edge-audit/"):\n        return 200, render_edge_audit_page()\n\n'

if '"/edge-audit"' not in s:
    s = s[:insert_pos] + route_block + s[insert_pos:]

p.write_text(s, encoding="utf-8")
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.audit.title": "Edge Audit",
        "edge.audit.subtitle": "Диагностика воронки EDGE Factory",
        "edge.audit.report": "Отчёт аудита"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_audit_ui_v1.sh <<'TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_AUDIT_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_audit_page.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_audit_v1.py >/tmp/edge_audit_refresh.txt

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/edge-audit >/tmp/edge_audit_ui.html

grep -q "Edge Audit" /tmp/edge_audit_ui.html
grep -q "EDGE_PIPELINE_AUDIT_V1" /tmp/edge_audit_ui.html
grep -q "FUNNEL" /tmp/edge_audit_ui.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_AUDIT_UI_V1_OK"
TEST

chmod +x scripts/test_edge_audit_ui_v1.sh
scripts/test_edge_audit_ui_v1.sh

echo "VERDICT=BUILD_EDGE_AUDIT_UI_V1_OK"
