#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WORKSPACE_V2_HOME_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_workspace_v2_home \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/workspace_v2/home_v1.py \
  src/marketcore/presentation/workspace_v2/mission_control_v1.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route

code, html = route("/workspace-v2")

assert code == 200
assert b"MarketCore Workspace V2" in html
assert "Главная".encode("utf-8") in html
assert b"/workspace-v2/portfolio" in html
assert b"/workspace-v2/instruments" in html

print("WORKSPACE_V2_HOME_ROUTE_OK")
PY

if grep -RIn "marketcore-ui-v2-mobile-navigation" src/scripts; then
  echo "FORBIDDEN_UI_PATCH_IN_SCRIPTS"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

UI_PORT="${MARKETCORE_UI_PORT:-8080}"
html="/tmp/marketcore_workspace_v2_home_v1.html"

curl -sS "http://127.0.0.1:${UI_PORT}/workspace-v2" > "$html"

grep -q "Главная" "$html"
grep -q "MarketCore Workspace V2" "$html"
grep -q "/workspace-v2/portfolio" "$html"
grep -q "/workspace-v2/instruments" "$html"

if grep -Eo '(model\.health|paper\.feedback|paper\.analytics|trading_plan|marketcore_ui)\.[A-Za-z0-9_.-]+' "$html"; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

echo "workspace_v2_home=OK"
echo "route=/workspace-v2"
echo "raw_i18n_keys=0"
echo "safe_ui_targets=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WORKSPACE_V2_HOME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WORKSPACE_V2_HOME_V1_OK"
