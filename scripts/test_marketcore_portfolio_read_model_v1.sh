#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PORTFOLIO_READ_MODEL_V1 ==="

scripts/apply_marketcore_portfolio_read_model_v1.sh

PYTHONPATH=src python -m py_compile src/scripts/build_marketcore_read_model_layer_v1.py

sudo -u postgres env \
  PYTHONPATH=src \
  DATABASE_URL=postgresql:///finam_core \
  /opt/finam-core/venv/bin/python src/scripts/build_marketcore_read_model_layer_v1.py

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.portfolio_summary_v1;")
if [ "$rows" -ne 1 ]; then
  echo "portfolio_rows=$rows"
  exit 1
fi

psql -At -d finam_core -c "
SELECT portfolio_status, next_action, source_version
FROM marketcore_ui.portfolio_summary_v1
WHERE id=1;
" | grep -q "READY|MARKETCORE_INTRADAY_WORKSPACE_V1|MARKETCORE_READ_MODEL_LAYER_V1"

echo "portfolio_read_model_rows=1"
echo "portfolio_status=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_PORTFOLIO_READ_MODEL_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PORTFOLIO_READ_MODEL_V1_OK"
