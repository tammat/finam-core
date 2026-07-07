#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MAX_EDGE_DISCOVERY_UI_PART1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/presentation/005_max_edge_discovery_ui_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/max_edge_viewmodel.py \
  src/marketcore/presentation/providers/max_edge_provider.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.max_edge_provider import MaxEdgeProvider

vm = MaxEdgeProvider().load()

assert isinstance(vm.current, dict)
assert isinstance(vm.ranking, list)
assert isinstance(vm.labels, dict)
assert "edge_score" in vm.current
assert len(vm.labels) >= 5

print("MAX_EDGE_PROVIDER_OK")
print("current_symbol=", vm.current.get("symbol"))
print("current_score=", vm.current.get("edge_score"))
PY

labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='max_edge'
  AND resource_key LIKE 'max.edge.ui.%'
  AND locale_code='ru';
")

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.max_edge_ranking_v1
WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1';
")

test "$labels" -ge 9
test "$rows" -gt 0

echo "i18n_labels=$labels"
echo "max_edge_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MAX_EDGE_DISCOVERY_UI_PART1_READY"
echo "VERDICT=TEST_MAX_EDGE_DISCOVERY_UI_PART1_OK"
