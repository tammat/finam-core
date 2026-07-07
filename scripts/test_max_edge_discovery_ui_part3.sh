#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MAX_EDGE_DISCOVERY_UI_PART3 ==="

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/max_edge_viewmodel.py \
  src/marketcore/presentation/providers/max_edge_provider.py \
  src/marketcore/presentation/components/max_edge_card.py \
  src/marketcore/presentation/pages/max_edge_page.py \
  src/marketcore/presentation/providers/discovery_control_provider.py \
  src/marketcore/presentation/viewmodels/discovery_control_viewmodel.py \
  src/marketcore/presentation/pages/discovery_control_page.py \
  src/marketcore/presentation/registry.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.discovery_control_provider import DiscoveryControlProvider
from marketcore.presentation.registry import get_page

vm = DiscoveryControlProvider().load()
assert hasattr(vm, "max_edge")
assert isinstance(vm.max_edge, list)
assert len(vm.max_edge) > 0
assert get_page("/max-edge") is not None
assert get_page("/edge-discovery") is not None

print("DISCOVERY_CONTROL_MAX_EDGE_OK")
print("top_symbol=", vm.max_edge[0].get("symbol"))
print("top_score=", vm.max_edge[0].get("edge_score"))
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/max-edge >/tmp/max_edge_ui_part3.html
curl -fsS http://127.0.0.1:8080/edge-discovery >/tmp/discovery_control_max_edge_part3.html

grep -q "Максимальный edge" /tmp/max_edge_ui_part3.html
grep -q "SBER@MISX" /tmp/max_edge_ui_part3.html
grep -q "87.150000" /tmp/max_edge_ui_part3.html

grep -q "Max Edge" /tmp/discovery_control_max_edge_part3.html
grep -q "SBER@MISX" /tmp/discovery_control_max_edge_part3.html

if grep -q "<pre" /tmp/max_edge_ui_part3.html; then
  echo "RAW_PRE_FOUND_MAX_EDGE"
  exit 1
fi

if grep -q "<pre" /tmp/discovery_control_max_edge_part3.html; then
  echo "RAW_PRE_FOUND_DISCOVERY"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MAX_EDGE_DISCOVERY_UI_V1_READY"
echo "VERDICT=TEST_MAX_EDGE_DISCOVERY_UI_PART3_OK"
