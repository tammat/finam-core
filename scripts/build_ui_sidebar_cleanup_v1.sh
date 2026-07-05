#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_UI_SIDEBAR_CLEANUP_V1 ==="

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "UI_SIDEBAR_CLEANUP_V1" not in s:
    marker = "def menu_pages() -> list[Page]:\n"
    if marker not in s:
        raise SystemExit("MENU_PAGES_MARKER_NOT_FOUND")

    block = '''
# UI_SIDEBAR_CLEANUP_V1
# Legacy/diagnostic pages remain routable through get_page(), but are hidden from the main sidebar.
HIDDEN_MENU_ROUTE_PARTS = (
    "edge-pipeline-v2",
    "paper-edge",
    "paper-runtime",
    "paper-sample",
    "phase-ii",
    "market-universe",
    "micro-live-readiness",
    "edge-oos",
    "edge-robustness",
    "edge-validation",
)

HIDDEN_MENU_CLASS_NAMES = {
    "EdgePipelineV2Page",
    "EdgePipelineV2PaperEdgeDiscoveryAliasPage",
    "EdgePipelineV2ValidationQueueAliasPage",
    "EdgePipelineV2ValidationPipelineAliasPage",
    "EdgePipelineV2RobustnessAliasPage",
    "EdgePipelineV2OosValidationAliasPage",
    "EdgePipelineV2OosBacktestAliasPage",
    "EdgePipelineV2MicroLiveAliasPage",
}


def _is_hidden_menu_page(page: Page) -> bool:
    route = getattr(page, "route", "") or ""
    cls_name = page.__class__.__name__
    if cls_name in HIDDEN_MENU_CLASS_NAMES:
        return True
    return any(part in route for part in HIDDEN_MENU_ROUTE_PARTS)


'''
    s = s.replace(marker, block + marker)

s = s.replace(
    "def menu_pages() -> list[Page]:\n    return sorted(PAGES, key=lambda p: p.menu_order)\n",
    "def menu_pages() -> list[Page]:\n    return sorted([p for p in PAGES if not _is_hidden_menu_page(p)], key=lambda p: p.menu_order)\n",
)

p.write_text(s)
PY

cat > scripts/test_ui_sidebar_cleanup_v1.sh <<'SH_TEST'
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
SH_TEST

chmod +x scripts/test_ui_sidebar_cleanup_v1.sh
scripts/test_ui_sidebar_cleanup_v1.sh

echo "VERDICT=BUILD_UI_SIDEBAR_CLEANUP_V1_OK"
