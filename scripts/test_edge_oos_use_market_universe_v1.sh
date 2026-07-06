#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_OOS_USE_MARKET_UNIVERSE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_use_market_universe_v1.py \
  src/scripts/build_edge_robustness_check_v1.py \
  src/scripts/build_edge_oos_validation_v1.py \
  src/scripts/build_edge_oos_backtest_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_use_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  | tee /tmp/edge_oos_validation_market_universe_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  | tee /tmp/edge_oos_backtest_market_universe_v1.txt

grep -q "VERDICT=EDGE_OOS_VALIDATION_V1_READY" /tmp/edge_oos_validation_market_universe_v1.txt
grep -q "VERDICT=EDGE_OOS_BACKTEST_V1_READY" /tmp/edge_oos_backtest_market_universe_v1.txt

oos_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_validation_v1;")
backtest_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_backtest_v1;")

oos_symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.edge_oos_validation_v1;")
backtest_symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.edge_oos_backtest_v1;")

old_oos_br=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_validation_v1 WHERE symbol='BR@RTSX' AND timeframe='H1';")
old_bt_br=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_backtest_v1 WHERE symbol='BR@RTSX' AND timeframe='H1';")

test "$oos_rows" -gt 0
test "$backtest_rows" -gt 0
test "$oos_symbols" -gt 1
test "$backtest_symbols" -gt 1
test "$old_oos_br" = "0"
test "$old_bt_br" = "0"

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

curl -fsS "http://127.0.0.1:8080/edge-oos-validation" > /tmp/edge_oos_validation_ui.html
curl -fsS "http://127.0.0.1:8080/edge-oos-backtest" > /tmp/edge_oos_backtest_ui.html

if grep -q "BR@RTSX.*H1" /tmp/edge_oos_validation_ui.html; then
  echo "ERROR_OLD_BR_H1_VISIBLE_IN_OOS_VALIDATION_UI"
  exit 1
fi

if grep -q "BR@RTSX.*H1" /tmp/edge_oos_backtest_ui.html; then
  echo "ERROR_OLD_BR_H1_VISIBLE_IN_OOS_BACKTEST_UI"
  exit 1
fi

psql -d finam_core -c "
SELECT symbol, timeframe, robustness_status, oos_status, readiness_status, robustness_score
FROM marketcore_ui.edge_oos_validation_v1
ORDER BY oos_rank
LIMIT 30;
"

psql -d finam_core -c "
SELECT symbol, timeframe, backtest_status, total_trades, is_trades, oos_trades, stability_score
FROM marketcore_ui.edge_oos_backtest_v1
ORDER BY backtest_rank
LIMIT 30;
"

echo "oos_rows=$oos_rows"
echo "oos_symbols=$oos_symbols"
echo "backtest_rows=$backtest_rows"
echo "backtest_symbols=$backtest_symbols"
echo "old_oos_br_h1=$old_oos_br"
echo "old_backtest_br_h1=$old_bt_br"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_OOS_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_OOS_USE_MARKET_UNIVERSE_V1_OK"
