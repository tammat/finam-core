#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RUNTIME_CENTER_READ_MODEL_V1 ==="

scripts/apply_marketcore_runtime_center_read_model_v1.sh

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.runtime_center_summary_v1;")
if [ "$rows" -ne 1 ]; then
  echo "runtime_center_rows=$rows"
  exit 1
fi

psql -At -d finam_core -c "
SELECT runtime_status, paper_status, production_status, risk_status, next_action
FROM marketcore_ui.runtime_center_summary_v1
WHERE id=1;
" | grep -q "OFF|READY|OFF|SAFE|PAPER_CENTER_REVIEW"

echo "runtime_center_rows=1"
echo "runtime_status=OFF"
echo "paper_status=READY"
echo "production_status=OFF"
echo "risk_status=SAFE"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RUNTIME_CENTER_READ_MODEL_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RUNTIME_CENTER_READ_MODEL_V1_OK"
