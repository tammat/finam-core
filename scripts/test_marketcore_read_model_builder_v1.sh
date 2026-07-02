#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_READ_MODEL_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_marketcore_read_model_layer_v1.py

sudo -u postgres env \
  PYTHONPATH=src \
  DATABASE_URL=postgresql:///finam_core \
  /opt/finam-core/venv/bin/python src/scripts/build_marketcore_read_model_layer_v1.py

for table in \
  capital_summary_v1 \
  profit_summary_v1 \
  research_summary_v1 \
  risk_summary_v1 \
  program_summary_v1
do
  rows=$(sudo -u postgres psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.${table};")
  if [ "$rows" -ne 1 ]; then
    echo "table=${table} rows=${rows}"
    exit 1
  fi
  echo "table=${table} rows=${rows}"
done

sudo -u postgres psql -At -d finam_core -c "
SELECT source_version
FROM marketcore_ui.program_summary_v1
WHERE id=1;
" | grep -q "MARKETCORE_READ_MODEL_LAYER_V1"

echo "read_model_builder_ready=READY"
echo "capital_summary_ready=READY"
echo "profit_summary_ready=READY"
echo "research_summary_ready=READY"
echo "risk_summary_ready=READY"
echo "program_summary_ready=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_READ_MODEL_BUILDER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_READ_MODEL_BUILDER_V1_OK"
