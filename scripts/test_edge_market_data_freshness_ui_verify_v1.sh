#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_MARKET_DATA_FRESHNESS_UI_VERIFY_V1 ==="

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_binding_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_freshness_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/paper-edge-market-data-freshness" \
  > /tmp/edge_market_data_freshness_ui.html

grep -q "USDRUBF@RTSX" /tmp/edge_market_data_freshness_ui.html
grep -q "SBER@MISX" /tmp/edge_market_data_freshness_ui.html
grep -q "GAZP@MISX" /tmp/edge_market_data_freshness_ui.html
grep -q "CANDIDATE_BOUND_FRESH" /tmp/edge_market_data_freshness_ui.html

if grep -q "BR@RTSX.*ANY" /tmp/edge_market_data_freshness_ui.html; then
  echo "ERROR_OLD_BR_ANY_VISIBLE_IN_UI"
  exit 1
fi

grep -R "paper_edge_research_candidates_v1" -n \
  src/marketcore/api \
  src/marketcore/presentation/pages \
  src/scripts \
  --exclude-dir="__pycache__" || true

echo "VERDICT=EDGE_MARKET_DATA_FRESHNESS_UI_VERIFY_V1_READY"
echo "VERDICT=TEST_EDGE_MARKET_DATA_FRESHNESS_UI_VERIFY_V1_OK"
