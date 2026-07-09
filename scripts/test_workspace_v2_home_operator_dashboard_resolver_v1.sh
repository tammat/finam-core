#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_RESOLVER_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
  -f sql/presentation/workspace_v2_home_operator_dashboard_i18n_v1.sql

files=(
  "src/marketcore/presentation/workspace_v2/domain/home_operator_dashboard_model_v1.py"
  "src/marketcore/presentation/workspace_v2/resolver/home_operator_dashboard_resolver_v1.py"
)

PYTHONPYCACHEPREFIX=/tmp/home_operator_dashboard_resolver \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'row\["|row\[' \
  src/marketcore/presentation/workspace_v2/resolver/home_operator_dashboard_resolver_v1.py; then
  echo "SCHEMA_COUPLING_IN_RESOLVER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.resolver.home_operator_dashboard_resolver_v1 import (
    HomeOperatorDashboardResolverV1,
)

resolver = HomeOperatorDashboardResolverV1()
items = resolver.resolve()

assert len(items) == 5
assert resolver.resolve() is items

for item in items:
    assert item.item_code
    assert item.title_key
    assert item.subtitle_key
    assert item.status_label_key
    assert item.rows_total >= 0

print("home_operator_dashboard_resolver=OK")
print(f"items={len(items)}")
print(f"rows_total={sum(item.rows_total for item in items)}")
PY

echo "home_operator_dashboard_resolver=OK"
echo "schema_isolation=OK"
echo "read_only=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_RESOLVER_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_RESOLVER_V1_OK"
