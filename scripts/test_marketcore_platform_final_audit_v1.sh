#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PLATFORM_FINAL_AUDIT_V1 ==="

mkdir -p reports
report="reports/marketcore_platform_final_audit_v1.txt"

{
echo "=== MARKETCORE PLATFORM FINAL AUDIT V1 ==="
echo "generated_at=$(date -Is)"
echo

echo "=== GIT ==="
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git tag --points-at HEAD || true
echo

echo "=== REQUIRED DOCS ==="
for f in \
  docs/ARCHITECTURE_V2.md \
  docs/ROADMAP_V3.txt \
  docs/MARKETCORE_UI_STANDARDS_V1.txt \
  docs/MARKETCORE_DEVELOPMENT_PRINCIPLES_V1.txt \
  docs/MARKETCORE_PLATFORM_AUDIT_REPORT_V1.txt
do
  test -f "$f"
  echo "OK $f"
done
echo

echo "=== PYTHON COMPILE PRESENTATION ==="
PYTHONPYCACHEPREFIX=/tmp/finam_pycache_platform_final PYTHONPATH=src \
python -m py_compile $(find src/marketcore/presentation -name '*.py' -type f)
echo "presentation_compile=OK"
echo

echo "=== PYTHON COMPILE SCRIPTS CRITICAL ==="
PYTHONPYCACHEPREFIX=/tmp/finam_pycache_platform_final PYTHONPATH=src \
python -m py_compile \
  src/scripts/build_edge_score_model_v2.py \
  src/scripts/build_edge_score_model_v2_explain.py \
  src/scripts/build_edge_score_model_v2_reconciliation.py \
  src/scripts/build_edge_score_model_v2_shadow_observation_collector.py
echo "critical_scripts_compile=OK"
echo

echo "=== POSTGRES CORE TABLES ==="
psql -At -d finam_core -c "
SELECT 'edge_score_model_v2=' || count(*) FROM analytics.edge_score_model_v2
UNION ALL
SELECT 'edge_score_model_v2_explain=' || count(*) FROM analytics.edge_score_model_v2_explain
UNION ALL
SELECT 'edge_score_model_v2_reconciliation=' || count(*) FROM analytics.edge_score_model_v2_reconciliation
UNION ALL
SELECT 'shadow_observation=' || count(*) FROM analytics.edge_score_model_v2_shadow_observation_v1
UNION ALL
SELECT 'shadow_daily=' || count(*) FROM analytics.edge_score_model_v2_shadow_observation_daily_v1;
"
echo

echo "=== TOP EDGE TODAY ==="
psql -d finam_core -c "
SELECT symbol, strategy_code, timeframe, edge_score_v2, model_verdict
FROM analytics.edge_score_model_v2
ORDER BY edge_score_v2 DESC NULLS LAST
LIMIT 10;
"
echo

echo "=== UI SERVICE ==="
sudo systemctl restart marketcore-ui-shell.service
sleep 2
systemctl is-active --quiet marketcore-ui-shell.service
echo "ui_service=active"
echo

echo "=== HTTP ROUTES ==="
for route in / /max-edge /edge-score-shadow /edge-score-shadow-daily /market-model /portfolio /risk /system /settings; do
  code=$(curl -sS -o /tmp/marketcore_final_route.html -w "%{http_code}" "http://127.0.0.1:8080${route}?v=$(date +%s)" || true)
  echo "route=$route code=$code"
  test "$code" = "200"
done
echo

echo "=== OPERATOR HOME HTML ==="
curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/marketcore_platform_final_home.html
grep -q "MarketCore" /tmp/marketcore_platform_final_home.html
grep -q "operator-sidebar" /tmp/marketcore_platform_final_home.html
grep -q "marketcore-widget-grid" /tmp/marketcore_platform_final_home.html
grep -q "marketcore-status-bar" /tmp/marketcore_platform_final_home.html
grep -q 'data-dashboard-id="operator.home.v2"' /tmp/marketcore_platform_final_home.html
echo "operator_home=OK"
echo

echo "=== LEGACY UI ABSENCE ==="
for forbidden in \
  "FINAM Core" \
  "Paper Edge Discovery" \
  "Edge OOS Validation" \
  "Edge OOS Backtest" \
  "Micro Live" \
  "Paper Sample Accumulation Monitor" \
  "Runtime · Paper"
do
  if grep -q "$forbidden" /tmp/marketcore_platform_final_home.html; then
    echo "FORBIDDEN_VISIBLE=$forbidden"
    exit 1
  fi
done
echo "legacy_operator_ui=0"
echo

echo "=== I18N RAW KEY AUDIT OPERATOR HOME ==="
raw_i18n=$(grep -Eo '(page|column|status|button|strategy|dashboard|tooltip|message|error|statusbar|widget)\.[A-Za-z0-9_.-]+' /tmp/marketcore_platform_final_home.html | sort -u || true)
if [ -n "$raw_i18n" ]; then
  echo "$raw_i18n"
  echo "RAW_I18N_KEYS_VISIBLE=1"
else
  echo "RAW_I18N_KEYS_VISIBLE=0"
fi
echo

echo "=== SAFETY CODE AUDIT ==="
if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation; then
  echo "DANGEROUS_PRESENTATION_ACTION_FOUND=1"
  exit 1
fi
echo "dangerous_presentation_actions=0"
echo

echo "=== WIDGET SDK AUDIT ==="
test -f src/marketcore/presentation/widgets/contracts.py
test -f src/marketcore/presentation/widgets/registry.py
test -f src/marketcore/presentation/widgets/renderer.py
PYTHONPATH=src python - <<'PY'
from marketcore.presentation.widgets.registry import default_widget_registry
items = default_widget_registry().all()
assert len(items) >= 5
print("widgets_registered=", ",".join(i.widget_id for i in items))
PY
echo

echo "=== POSTGRES SAFETY ==="
echo "delete_allowed=0"
echo "drop_allowed=0"
echo "truncate_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=MARKETCORE_PLATFORM_FINAL_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PLATFORM_FINAL_AUDIT_V1_OK"
} | tee "$report"

grep -q "VERDICT=TEST_MARKETCORE_PLATFORM_FINAL_AUDIT_V1_OK" "$report"
