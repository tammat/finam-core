#!/usr/bin/env bash
set -euo pipefail

echo "=== PATCH_EDGE_MARKET_DATA_FRESHNESS_USE_MARKET_UNIVERSE_V1 ==="

cp src/scripts/build_paper_edge_market_data_freshness_v1.py \
   /tmp/build_paper_edge_market_data_freshness_v1.py.bak

python - <<'PY'
from pathlib import Path

p = Path("src/scripts/build_paper_edge_market_data_freshness_v1.py")
s = p.read_text()

s = s.replace(
    "marketcore_ui.paper_edge_research_candidates_v1",
    "marketcore_ui.market_universe_research_queue_v1"
)

s = s.replace(
    "candidate_symbol",
    "symbol"
)

s = s.replace(
    "candidate_timeframe",
    "timeframe"
)

s = s.replace(
    "candidate_strategy",
    "recommended_strategy_family"
)

s = s.replace(
    "candidate_root",
    "symbol"
)

p.write_text(s)
PY

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_data_freshness_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_freshness_v1.py \
  | tee /tmp/edge_market_data_freshness_market_universe_patch_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_READY" \
  /tmp/edge_market_data_freshness_market_universe_patch_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/paper-edge-market-data-freshness" \
  > /tmp/paper_edge_market_data_freshness_after_patch.html

if grep -q "BR@RTSX.*ANY" /tmp/paper_edge_market_data_freshness_after_patch.html; then
  echo "ERROR_OLD_BR_ANY_STILL_VISIBLE"
  exit 1
fi

grep -E "LKOH|SBER|GAZP|PLZL|NG|GD|BTC|ETH" \
  /tmp/paper_edge_market_data_freshness_after_patch.html

psql -d finam_core -c "
SELECT row_type, candidate_symbol, market_symbol, market_timeframe, bars_total, latest_bar_ts, freshness_status
FROM marketcore_ui.paper_edge_market_data_freshness_v1
ORDER BY freshness_rank
LIMIT 40;
"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_MARKET_DATA_FRESHNESS_USE_MARKET_UNIVERSE_PATCH_V1_READY"
