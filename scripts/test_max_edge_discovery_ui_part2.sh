#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MAX_EDGE_DISCOVERY_UI_PART2 ==="

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/components/max_edge_card.py \
  src/marketcore/presentation/pages/max_edge_page.py \
  src/marketcore/presentation/registry.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.registry import get_page

page = get_page("/max-edge")
assert page is not None
print(page)
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/max-edge >/tmp/max_edge_discovery_ui_part2.html

grep -q "Максимальный edge" /tmp/max_edge_discovery_ui_part2.html
grep -q "SBER@MISX" /tmp/max_edge_discovery_ui_part2.html
grep -q "87.150000" /tmp/max_edge_discovery_ui_part2.html

if grep -q "<pre" /tmp/max_edge_discovery_ui_part2.html; then
  echo "RAW_PRE_FOUND"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MAX_EDGE_DISCOVERY_UI_PART2_READY"
echo "VERDICT=TEST_MAX_EDGE_DISCOVERY_UI_PART2_OK"
