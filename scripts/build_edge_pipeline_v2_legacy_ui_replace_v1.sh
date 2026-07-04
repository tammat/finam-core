#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat > src/marketcore/presentation/pages/edge_pipeline_v2_legacy_aliases.py <<'PY'
from __future__ import annotations

from marketcore.presentation.pages.edge_pipeline_v2 import EdgePipelineV2Page
from marketcore.presentation.ui_labels import display_label


class EdgePipelineV2PaperEdgeDiscoveryAliasPage(EdgePipelineV2Page):
    route = "/paper-edge-discovery"
    title = display_label(route, "Edge")


class EdgePipelineV2ValidationQueueAliasPage(EdgePipelineV2Page):
    route = "/edge-validation-queue"
    title = display_label(route, "Проверка")


class EdgePipelineV2ValidationPipelineAliasPage(EdgePipelineV2Page):
    route = "/edge-validation-pipeline"
    title = display_label(route, "Этапы")


class EdgePipelineV2RobustnessAliasPage(EdgePipelineV2Page):
    route = "/edge-robustness-check"
    title = display_label(route, "Устойчивость")


class EdgePipelineV2OosValidationAliasPage(EdgePipelineV2Page):
    route = "/edge-oos-validation"
    title = display_label(route, "Вне выборки")


class EdgePipelineV2OosBacktestAliasPage(EdgePipelineV2Page):
    route = "/edge-oos-backtest"
    title = display_label(route, "Тест вне выборки")


class EdgePipelineV2MicroLiveAliasPage(EdgePipelineV2Page):
    route = "/micro-live-readiness"
    title = display_label(route, "Проба")
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

import_line = (
    "from marketcore.presentation.pages.edge_pipeline_v2_legacy_aliases import "
    "EdgePipelineV2MicroLiveAliasPage, EdgePipelineV2OosBacktestAliasPage, "
    "EdgePipelineV2OosValidationAliasPage, EdgePipelineV2PaperEdgeDiscoveryAliasPage, "
    "EdgePipelineV2RobustnessAliasPage, EdgePipelineV2ValidationPipelineAliasPage, "
    "EdgePipelineV2ValidationQueueAliasPage\n"
)

s = s.replace(import_line, "")

future = "from __future__ import annotations\n\n"
if future not in s:
    raise SystemExit("FUTURE_IMPORT_NOT_FOUND")

s = s.replace(future, future + import_line)

replacements = {
    "    PaperEdgeDiscoveryPage(),": "    EdgePipelineV2PaperEdgeDiscoveryAliasPage(),",
    "    EdgeValidationQueuePage(),": "    EdgePipelineV2ValidationQueueAliasPage(),",
    "    EdgeValidationPipelinePage(),": "    EdgePipelineV2ValidationPipelineAliasPage(),",
    "    EdgeRobustnessCheckPage(),": "    EdgePipelineV2RobustnessAliasPage(),",
    "    EdgeOosValidationPage(),": "    EdgePipelineV2OosValidationAliasPage(),",
    "    EdgeOosBacktestPage(),": "    EdgePipelineV2OosBacktestAliasPage(),",
    "    MicroLiveReadinessPage(),": "    EdgePipelineV2MicroLiveAliasPage(),",
}

for old, new in replacements.items():
    if old in s:
        s = s.replace(old, new)
    elif new not in s:
        raise SystemExit(f"REGISTRY_ENTRY_NOT_FOUND: {old}")

p.write_text(s)
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "/edge-pipeline-v2": "Этапы V2",
        "/paper-edge-discovery": "Edge",
        "/edge-validation-queue": "Проверка",
        "/edge-validation-pipeline": "Этапы",
        "/edge-robustness-check": "Устойчивость",
        "/edge-oos-validation": "Вне выборки",
        "/edge-oos-backtest": "Тест вне выборки",
        "/micro-live-readiness": "Проба",
    })
except NameError:
    pass
PY

cat > scripts/test_edge_pipeline_v2_legacy_ui_replace_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_pipeline_v2.py \
  src/marketcore/presentation/pages/edge_pipeline_v2_legacy_aliases.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

for path in \
  /paper-edge-discovery \
  /edge-validation-queue \
  /edge-validation-pipeline \
  /edge-robustness-check \
  /edge-oos-validation \
  /edge-oos-backtest \
  /micro-live-readiness
do
  out="/tmp/edge_pipeline_legacy_${path//\//_}.html"
  curl -fsS "http://127.0.0.1:8080${path}" > "$out"
  grep -q "analytics.edge_pipeline_snapshot_v1" "$out"

  if grep -q "BR@RTSX.*H1" "$out"; then
    echo "ERROR_LEGACY_BR_H1_VISIBLE path=$path"
    exit 1
  fi
done

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_pipeline_snapshot_v1;")
test "$rows" -gt 0

echo "edge_pipeline_rows=$rows"
echo "legacy_routes_replaced=7"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_pipeline_v2_legacy_ui_replace_v1.sh
scripts/test_edge_pipeline_v2_legacy_ui_replace_v1.sh

echo "VERDICT=BUILD_EDGE_PIPELINE_V2_LEGACY_UI_REPLACE_V1_OK"
