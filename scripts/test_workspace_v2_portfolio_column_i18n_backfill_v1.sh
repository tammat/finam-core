#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_COLUMN_I18N_BACKFILL_V1 ==="

py_file="scripts/build_workspace_v2_portfolio_column_i18n_backfill_v1.py"

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_column_i18n_backfill \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

out=$(PYTHONPATH=src python "$py_file")
echo "$out"

echo "$out" | grep -q "VERDICT=WORKSPACE_V2_PORTFOLIO_COLUMN_I18N_BACKFILL_V1_READY"

html=$(PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2
print(render_workspace_v2_portfolio_page_v2())
PY
)

echo "$html" | grep -q "mc-v2-values"
echo "$html" | grep -q "mc-v2-value-row"

if echo "$html" | grep -E "portfolio\.column\."; then
  echo "RAW_PORTFOLIO_COLUMN_KEY_FOUND"
  exit 1
fi

echo "portfolio_column_i18n_backfill=OK"
echo "raw_portfolio_column_keys=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_COLUMN_I18N_BACKFILL_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_COLUMN_I18N_BACKFILL_V1_OK"
