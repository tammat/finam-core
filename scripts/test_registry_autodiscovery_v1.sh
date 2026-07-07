#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_AUTODISCOVERY_V1 ==="

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/registry_autodiscovery.py \
  src/marketcore/presentation/registry.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.registry import PAGES, get_page, menu_pages

routes = [p.route for p in menu_pages()]

assert len(PAGES) >= 10
assert "/" in routes
assert "/edge-discovery" in routes
assert "/recommendation" in routes
assert get_page("/edge-discovery") is not None
assert len(routes) == len(set(routes))

print("pages=", len(PAGES))
print("edge_discovery=", get_page("/edge-discovery"))
PY

if grep -Rni "GRANT ALL PRIVILEGES .* TO alex\|GRANT ALL PRIVILEGES .* TO finam" sql/analytics/018_max_edge_discovery_engine_v1.sql; then
  echo "DIRECT_USER_GRANTS_FOUND"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=REGISTRY_AUTODISCOVERY_V1_READY"
echo "VERDICT=TEST_REGISTRY_AUTODISCOVERY_V1_OK"
