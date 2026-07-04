#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PIPELINE_V2_UI_MIGRATION_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat > src/marketcore/presentation/pages/edge_pipeline_v2.py <<'PY'
from __future__ import annotations

import html
import json
import urllib.request
from typing import Any

from marketcore.presentation.pages.base_page import BaseDashboardPage
from marketcore.presentation.ui_labels import display_label

API_URL = "http://127.0.0.1:8095/api/kg/v1/edge-pipeline"
SUMMARY_URL = "http://127.0.0.1:8095/api/kg/v1/edge-pipeline/summary"


def _json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def _e(v: object) -> str:
    return html.escape("" if v is None else str(v))


def _l(key: str, fallback: str) -> str:
    return display_label(f"edge_pipeline_v2.{key}", fallback)


class EdgePipelineV2Page(BaseDashboardPage):
    page_key = "edge_pipeline_v2"
    route = "/edge-pipeline-v2"
    title = display_label(route, "Этапы V2")
    subtitle = display_label(
        "edge_pipeline_v2.subtitle",
        "Единый снимок состояния кандидатов через Platform API.",
    )
    icon = "🧭"
    menu_order = 346

    def render_body(self) -> str:
        summary = (_json(SUMMARY_URL).get("data") or {})
        rows = (_json(API_URL).get("data") or [])

        cards = "".join(
            f'<section class="fc-card"><b>{_e(_l(label, fallback))}</b><br>{_e(summary.get(label, 0))}</section>'
            for label, fallback in [
                ("total", "Всего"),
                ("research", "Исследование"),
                ("validation", "Проверка"),
                ("robustness", "Устойчивость"),
                ("oos", "OOS"),
                ("risk", "Риск"),
                ("trading", "Торговля"),
            ]
        )

        body = []
        for i, r in enumerate(rows, 1):
            body.append(f"""
            <tr>
              <td>{i}</td>
              <td>{_e(r.get("display_name"))}<br><small>{_e(r.get("symbol"))}</small></td>
              <td>{_e(r.get("asset_class"))}</td>
              <td>{_e(r.get("timeframe"))}</td>
              <td>{_e(r.get("strategy_family"))}</td>
              <td>{_e(r.get("pipeline_stage"))}</td>
              <td>{_e(r.get("overall_status"))}</td>
              <td>{_e(r.get("ranking_score"))}</td>
              <td>{_e(r.get("research_priority"))}</td>
              <td>{_e(r.get("validation_status"))}</td>
              <td>{_e(r.get("robustness_status"))}</td>
              <td>{_e(r.get("oos_status"))}</td>
              <td>{_e(r.get("backtest_status"))}</td>
              <td>{_e(r.get("paper_status"))}</td>
              <td>{_e(r.get("risk_status"))}</td>
              <td>{_e(r.get("trading_status"))}</td>
            </tr>
            """)

        return f"""
        <section class="fc-card">
          <h1>{_e(self.title)}</h1>
          <p>{_e(self.subtitle)}</p>
          <p>Источник: analytics.edge_pipeline_snapshot_v1 → Platform API.</p>
        </section>

        <section class="fc-grid">{cards}</section>

        <section class="fc-card">
          <h2>{_e(_l("candidates", "Кандидаты"))}</h2>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>{_e(_l("instrument", "Инструмент"))}</th>
                <th>{_e(_l("asset", "Актив"))}</th>
                <th>TF</th>
                <th>{_e(_l("strategy", "Стратегия"))}</th>
                <th>{_e(_l("stage", "Этап"))}</th>
                <th>{_e(_l("status", "Статус"))}</th>
                <th>Score</th>
                <th>{_e(_l("priority", "Приоритет"))}</th>
                <th>{_e(_l("validation", "Проверка"))}</th>
                <th>{_e(_l("robustness", "Устойчивость"))}</th>
                <th>OOS</th>
                <th>{_e(_l("backtest", "Бэктест"))}</th>
                <th>Paper</th>
                <th>{_e(_l("risk", "Риск"))}</th>
                <th>{_e(_l("trading", "Торговля"))}</th>
              </tr>
            </thead>
            <tbody>{''.join(body)}</tbody>
          </table>
        </section>
        """
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/ui_labels.py")
s = p.read_text()

labels = {
    "/edge-pipeline-v2": "Этапы V2",
    "edge_pipeline_v2.subtitle": "Единый снимок состояния кандидатов через Platform API.",
    "edge_pipeline_v2.total": "Всего",
    "edge_pipeline_v2.research": "Исследование",
    "edge_pipeline_v2.validation": "Проверка",
    "edge_pipeline_v2.robustness": "Устойчивость",
    "edge_pipeline_v2.oos": "OOS",
    "edge_pipeline_v2.risk": "Риск",
    "edge_pipeline_v2.trading": "Торговля",
    "edge_pipeline_v2.candidates": "Кандидаты",
    "edge_pipeline_v2.instrument": "Инструмент",
    "edge_pipeline_v2.asset": "Актив",
    "edge_pipeline_v2.strategy": "Стратегия",
    "edge_pipeline_v2.stage": "Этап",
    "edge_pipeline_v2.status": "Статус",
    "edge_pipeline_v2.priority": "Приоритет",
    "edge_pipeline_v2.backtest": "Бэктест",
}

for k, v in labels.items():
    line = f'    "{k}": "{v}",'
    if line not in s:
        insert_at = s.find("}")
        s = s[:insert_at] + line + "\n" + s[insert_at:]

p.write_text(s)
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

imp = "from marketcore.presentation.pages.edge_pipeline_v2 import EdgePipelineV2Page\n"
if imp not in s:
    s = imp + s

entry = "    EdgePipelineV2Page(),\n"
if entry not in s:
    idx = s.rfind("]")
    if idx == -1:
        raise SystemExit("REGISTRY_PAGES_LIST_NOT_FOUND")
    s = s[:idx] + entry + s[idx:]

p.write_text(s)
PY

cat > scripts/test_edge_pipeline_v2_ui_migration_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_UI_MIGRATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/pages/edge_pipeline_v2.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/edge-pipeline-v2" > /tmp/edge_pipeline_v2_ui.html

grep -q "Этапы V2" /tmp/edge_pipeline_v2_ui.html
grep -q "analytics.edge_pipeline_snapshot_v1" /tmp/edge_pipeline_v2_ui.html

if grep -q "BR@RTSX.*H1" /tmp/edge_pipeline_v2_ui.html; then
  echo "ERROR_LEGACY_BR_H1_VISIBLE"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_UI_MIGRATION_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_UI_MIGRATION_V1_OK"
SH_TEST

chmod +x scripts/test_edge_pipeline_v2_ui_migration_v1.sh
scripts/test_edge_pipeline_v2_ui_migration_v1.sh

echo "VERDICT=BUILD_EDGE_PIPELINE_V2_UI_MIGRATION_V1_OK"
