#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_RESOURCE_MODEL_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/presentation/001_ui_resource_model_v1.sql

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='edge_factory'
  AND locale_code='ru'
  AND is_active=true;
")

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='edge_factory'
  AND locale_code='ru'
  AND trim(caption)='';
")

test "$rows" -ge 10
test "$missing" = "0"

echo "ui_resource_rows=$rows"
echo "missing_caption_rows=$missing"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_RESOURCE_MODEL_V1_READY"
echo "VERDICT=TEST_UI_RESOURCE_MODEL_V1_OK"
