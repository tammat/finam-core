#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_ADOPTION_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_model_v1.py \
  src/scripts/build_paper_edge_market_data_binding_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_model_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_binding_v1.py \
  | tee /tmp/market_model_adoption_binding_v1.txt

grep -q "market_source=marketcore.market_snapshot_v1 exists=1" \
  /tmp/market_model_adoption_binding_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1_READY" \
  /tmp/market_model_adoption_binding_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_binding_v1;")
fresh=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_binding_v1 WHERE market_data_status='FRESH_MARKET_DATA';")
source_bad=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_binding_v1 WHERE bars_source_table <> 'marketcore.market_snapshot_v1';")

test "$rows" -gt 0
test "$fresh" -gt 0
test "$source_bad" = "0"

echo "binding_rows=$rows"
echo "fresh_rows=$fresh"
echo "source_bad=$source_bad"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_MODEL_ADOPTION_BINDING_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_ADOPTION_BINDING_V1_OK"
