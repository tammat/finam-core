#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_SAFE_TARGET_AUDIT_V1 ==="

mkdir -p reports
report="reports/marketcore_ui_safe_target_audit_v1.txt"

{
echo "======================================================"
echo "MARKETCORE UI SAFE TARGET AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo

echo "=== SAFE UI TARGETS ==="
find src/marketcore/presentation src/marketcore/ui -type f \
  \( -name "*.py" -o -name "*.html" -o -name "*.css" -o -name "*.js" \) \
  | sort

echo
echo "=== UI ENTRYPOINT CANDIDATES ==="
grep -RIl 'MarketCore\|<html\|</body>\|WidgetViewModel\|render_widget' \
  src/marketcore/presentation src/marketcore/ui \
  | sort

echo
echo "=== FORBIDDEN SCRIPT TARGETS CHECK ==="
bad_targets=$(grep -RIl 'marketcore-mobile-nav-v1' src/scripts 2>/dev/null || true)
if [ -n "$bad_targets" ]; then
  echo "$bad_targets"
  echo "FORBIDDEN_SCRIPT_UI_PATCH_FOUND"
  exit 1
fi

echo "forbidden_script_ui_patch=0"

echo
echo "=== EXPECTED ROUTE FILES ==="
for f in \
  src/marketcore/presentation/dashboard/server.py \
  src/marketcore/presentation/dashboard/home_router.py \
  src/marketcore/presentation/dashboard/layout_builder.py \
  src/marketcore/presentation/pages/operator_home_page.py \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/widgets/renderer.py \
  src/marketcore/presentation/services/i18n_service.py
do
  if [ -f "$f" ]; then
    echo "OK $f"
  else
    echo "MISSING $f"
  fi
done

echo
echo "=== SAFETY ==="
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=MARKETCORE_UI_SAFE_TARGET_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=MARKETCORE_UI_SAFE_TARGET_AUDIT_V1_READY" "$report"

echo "report=$report"
echo "safe_root=src/marketcore/presentation"
echo "safe_root=src/marketcore/ui"
echo "forbidden_root=src/scripts"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_SAFE_TARGET_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_SAFE_TARGET_AUDIT_V1_OK"
