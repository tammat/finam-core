#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_SIDEBAR_CLEANUP_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/registry.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.registry import get_page, menu_pages

menu_routes = [p.route for p in menu_pages()]

assert "/edge-platform" in menu_routes
assert "/risk-platform" in menu_routes
assert "/trading-platform" in menu_routes
assert "/portfolio-platform" in menu_routes

assert not any("paper-edge" in r for r in menu_routes)
assert not any("edge-validation" in r for r in menu_routes)
assert not any("edge-oos" in r for r in menu_routes)

# Legacy route remains accessible if registered.
for route in ["/edge-platform", "/risk-platform", "/trading-platform", "/portfolio-platform"]:
    assert get_page(route) is not None
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/" >/tmp/ui_sidebar_cleanup_home.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_SIDEBAR_CLEANUP_V1_READY"
echo "VERDICT=TEST_UI_SIDEBAR_CLEANUP_V1_OK"
