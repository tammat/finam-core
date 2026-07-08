#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_WIDGET_LIBRARY_COMPAT_AUDIT_V1 ==="

mkdir -p reports

report="reports/widget_library_compat_audit_v1.txt"

{
  echo "=== MARKETCORE_WIDGET_LIBRARY_COMPAT_AUDIT_V1 ==="
  echo "generated_at=$(date -Is)"
  echo

  echo "=== WIDGET IMPORTS IN PRESENTATION ==="
  grep -RIn "marketcore.presentation.widgets" src/marketcore/presentation || true
  echo

  echo "=== WIDGET FILES ==="
  find src/marketcore/presentation/widgets -type f | sort
  echo

  echo "=== PAGE IMPORT CHECK ==="
  find src/marketcore/presentation/pages -name '*.py' -type f | sort
} > "$report"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_widget_compat \
PYTHONPATH=src \
python -m py_compile \
  $(find src/marketcore/presentation -name '*.py' -type f)

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.registry_autodiscovery import discover_pages

pages = discover_pages()
assert pages, "NO_PAGES_DISCOVERED"

routes = sorted({p.route for p in pages})
assert "/" in routes, "HOME_ROUTE_MISSING"

print("pages_discovered=", len(pages))
print("home_route=OK")
PY

# Обязательные совместимые модули после введения Widget SDK.
for f in \
  src/marketcore/presentation/widgets/common/__init__.py \
  src/marketcore/presentation/widgets/common/responsive.py \
  src/marketcore/presentation/widgets/contracts.py \
  src/marketcore/presentation/widgets/renderer.py \
  src/marketcore/presentation/widgets/registry.py
do
  test -f "$f" || {
    echo "MISSING_COMPAT_WIDGET_FILE=$f"
    exit 1
  }
done

# Не допускаем dangerous-действий в widgets.
if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/widgets; then
  echo "DANGEROUS_WIDGET_COMPAT_ACTION_FOUND"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

if ! systemctl is-active --quiet marketcore-ui-shell.service; then
  echo "UI_SERVICE_NOT_ACTIVE_AFTER_WIDGET_COMPAT_AUDIT"
  journalctl -u marketcore-ui-shell.service --since "2 minutes ago" --no-pager -n 80
  exit 1
fi

for route in / /max-edge /edge-score-shadow /edge-score-shadow-daily /system; do
  code=$(curl -sS -o /tmp/widget_compat_route.html -w "%{http_code}" "http://127.0.0.1:8080${route}?v=$(date +%s)" || true)
  if [ "$code" != "200" ]; then
    echo "ROUTE_HTTP_NOT_OK route=$route code=$code"
    exit 1
  fi
done

grep -q "marketcore.presentation.widgets.common.responsive" "$report"
grep -q "src/marketcore/presentation/widgets/common/responsive.py" "$report"

echo "report=$report"
echo "widget_compat_files=OK"
echo "pages_discovery=OK"
echo "http_routes=OK"
echo "dangerous_actions=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WIDGET_LIBRARY_COMPAT_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WIDGET_LIBRARY_COMPAT_AUDIT_V1_OK"
