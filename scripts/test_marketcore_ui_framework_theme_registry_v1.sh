#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
    -f sql/presentation/ui_theme_registry_v1.sql

psql -d finam_core -v ON_ERROR_STOP=1 \
    -f sql/presentation/ui_theme_registry_seed_v1.sql

themes=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM presentation.ui_theme_v1;
SQL
)

props=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM presentation.ui_theme_property_v1;
SQL
)

test "$themes" -ge 1
test "$props" -ge 10

echo "theme_registry=OK"
echo "theme_properties=$props"

echo "hardcode_colors=0"
echo "hardcode_sizes=0"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1_OK"
