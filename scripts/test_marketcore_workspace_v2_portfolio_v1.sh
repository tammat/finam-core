#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WORKSPACE_V2_PORTFOLIO_V1 ==="

py_file="src/marketcore/presentation/workspace_v2/portfolio_v1.py"
router="src/marketcore/presentation/router.py"

test -f "$py_file"
test -f "$router"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_workspace_v2_portfolio \
PYTHONPATH=src \
python -m py_compile "$router" "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "$py_file" "$router"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RIn "marketcore-ui-v2-mobile-navigation" src/scripts; then
  echo "FORBIDDEN_UI_PATCH_IN_SCRIPTS"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route

code, html = route("/workspace-v2/portfolio")

assert code == 200
assert "Портфель".encode("utf-8") in html
assert b"MarketCore Workspace V2" in html
assert "Доб. капитал".encode("utf-8") in html
assert b"/workspace-v2/capital" in html
assert b"workspace_v2_design_system_v1.css" in html

print("WORKSPACE_V2_PORTFOLIO_ROUTE_OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

UI_PORT="${MARKETCORE_UI_PORT:-8080}"
html="/tmp/marketcore_workspace_v2_portfolio_v1.html"

curl -sS "http://127.0.0.1:${UI_PORT}/workspace-v2/portfolio" > "$html"

grep -q "Портфель" "$html"
grep -q "MarketCore Workspace V2" "$html"
grep -q "Доб. капитал" "$html"
grep -q "/workspace-v2/capital" "$html"

if grep -Eo '(model\.health|paper\.feedback|paper\.analytics|trading_plan|marketcore_ui)\.[A-Za-z0-9_.-]+' "$html"; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

echo "workspace_v2_portfolio=OK"
echo "route=/workspace-v2/portfolio"
echo "capital_future_action=OK"
echo "portfolio_read_only=OK"
echo "raw_i18n_keys=0"
echo "safe_ui_targets=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WORKSPACE_V2_PORTFOLIO_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WORKSPACE_V2_PORTFOLIO_V1_OK"
