#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_I18N_ARCHITECTURE_V1 ==="

files=(
  src/marketcore/presentation/localization.py
  src/marketcore/presentation/i18n/__init__.py
  src/marketcore/presentation/i18n/registry.py
  src/scripts/build_marketcore_ui_i18n_registry.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_i18n_arch PYTHONPATH=src python -m py_compile "$f"
done

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_i18n_arch PYTHONPATH=src python src/scripts/build_marketcore_ui_i18n_registry.py)
echo "$out"

echo "$out" | grep -q "invalid_prefixes=0"
echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"
echo "$out" | grep -q "orders_changed=0"
echo "$out" | grep -q "fills_changed=0"
echo "$out" | grep -q "micro_live_allowed=0"
echo "$out" | grep -q "VERDICT=MARKETCORE_UI_I18N_ARCHITECTURE_V1_READY"

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('page.max_edge.title'),
    ('page.shadow.title'),
    ('page.shadow.daily.title'),
    ('column.symbol'),
    ('column.strategy'),
    ('column.score'),
    ('column.status'),
    ('status.pass'),
    ('status.review'),
    ('status.done'),
    ('status.waiting'),
    ('status.active'),
    ('status.disabled'),
    ('button.refresh'),
    ('button.open'),
    ('button.back'),
    ('button.home')
) AS required(resource_key)
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=required.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

if [ "$missing" != "0" ]; then
  echo "MISSING_I18N_ARCH_RESOURCES=$missing"
  exit 1
fi

if grep -RInE 'send_order|place_order|cancel_order|execute_order|FinamClient|LiveExecution|PaperExecution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' \
  src/marketcore/presentation/i18n \
  src/marketcore/presentation/localization.py \
  src/scripts/build_marketcore_ui_i18n_registry.py; then
  echo "DANGEROUS_I18N_ARCH_ACTION_FOUND"
  exit 1
fi

echo "missing_i18n_resources=0"
echo "dangerous_actions=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_I18N_ARCHITECTURE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_I18N_ARCHITECTURE_V1_OK"
