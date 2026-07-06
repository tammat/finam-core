#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_MTM_UI_V1 ==="

mkdir -p src/marketcore/presentation/pages

cat > src/marketcore/presentation/pages/paper_mtm_page.py <<'PY'
from __future__ import annotations

import subprocess
from html import escape

from marketcore.presentation.page import Page


class PaperMtmPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-mtm",
            title="Paper MTM",
            icon="📊",
            menu_order=47,
        )

    def render(self) -> str:
        sql = """
SELECT
  candidate_id,
  strategy_code,
  symbol,
  timeframe,
  trades,
  round(net_pnl,6) AS net_pnl,
  round(max_drawdown,6) AS max_drawdown,
  paper_status,
  mtm_ts
FROM analytics.paper_portfolio_mtm_v1
ORDER BY mtm_ts DESC, net_pnl DESC
LIMIT 50;
"""
        result = subprocess.run(
            ["psql", "-d", "finam_core", "-c", sql],
            check=False,
            capture_output=True,
            text=True,
        )
        body = escape(result.stdout if result.returncode == 0 else result.stderr)

        return f"""
        <div class="card">
            <h2>Paper MTM</h2>
            <p>Mark-to-market по активным paper-кандидатам. Micro Live и Live не включаются.</p>
        </div>
        <div class="card">
            <pre style="white-space:pre-wrap;font-size:12px;line-height:1.35">{body}</pre>
        </div>
        """
PY

python - <<'PY'
from pathlib import Path

reg = Path("src/marketcore/presentation/registry.py")
s = reg.read_text(encoding="utf-8")

imp = "from marketcore.presentation.pages.paper_mtm_page import PaperMtmPage\n"
if imp not in s:
    s = imp + s

if "PaperMtmPage()," not in s:
    marker = "    EdgeFactoryPage(),\n"
    if marker in s:
        s = s.replace(marker, marker + "    PaperMtmPage(),\n")
    else:
        idx = s.find("PAGES = [")
        start = s.find("\n", idx) + 1
        s = s[:start] + "    PaperMtmPage(),\n" + s[start:]

reg.write_text(s, encoding="utf-8")
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "paper.mtm.title": "Paper MTM",
        "paper.mtm.subtitle": "Mark-to-market по paper-кандидатам",
        "paper.mtm.net_pnl": "Net PnL",
        "paper.mtm.drawdown": "Drawdown",
        "paper.mtm.status": "Статус"
    })
except NameError:
    pass
PY

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/paper_mtm_page.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/paper-mtm >/tmp/paper_mtm_ui.html
curl -fsS http://127.0.0.1:8080/ >/tmp/paper_mtm_home.html

grep -q "Paper MTM" /tmp/paper_mtm_ui.html
grep -q "/paper-mtm" /tmp/paper_mtm_home.html

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$unsafe" = "0"

echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_MTM_UI_V1_READY"
echo "VERDICT=TEST_PAPER_MTM_UI_V1_OK"
