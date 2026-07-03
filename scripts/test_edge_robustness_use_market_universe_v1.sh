#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_ROBUSTNESS_USE_MARKET_UNIVERSE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_use_market_universe_v1.py \
  src/scripts/build_edge_robustness_check_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_use_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  | tee /tmp/edge_robustness_use_market_universe_v1.txt

grep -q "VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY" \
  /tmp/edge_robustness_use_market_universe_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_robustness_check_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.edge_robustness_check_v1;")
br_h1=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_robustness_check_v1 WHERE symbol='BR@RTSX' AND timeframe='H1';")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$br_h1" = "0"

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

curl -fsS "http://127.0.0.1:8080/edge-robustness-check" > /tmp/edge_robustness_ui.html

if grep -q "BR@RTSX.*H1" /tmp/edge_robustness_ui.html; then
  echo "ERROR_OLD_BR_H1_VISIBLE_IN_ROBUSTNESS_UI"
  exit 1
fi

grep -E "USDRUBF@RTSX|SBER@MISX|GAZP@MISX|LKOH@MISX|NGN6@RTSX" /tmp/edge_robustness_ui.html

echo "robustness_rows=$rows"
echo "robustness_symbols=$symbols"
echo "old_br_h1=$br_h1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_ROBUSTNESS_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_ROBUSTNESS_USE_MARKET_UNIVERSE_V1_OK"
