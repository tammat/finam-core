#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/run_edge_discovery_from_market_universe_cycle_v1.py \
  src/scripts/build_edge_discovery_from_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/run_edge_discovery_from_market_universe_cycle_v1.py \
  | tee /tmp/edge_discovery_market_universe_cycle_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_CYCLE_V1_READY" \
  /tmp/edge_discovery_market_universe_cycle_v1.txt

sudo cp deploy/systemd/finam-edge-discovery-market-universe.service /etc/systemd/system/
sudo cp deploy/systemd/finam-edge-discovery-market-universe.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finam-edge-discovery-market-universe.timer
sudo systemctl start finam-edge-discovery-market-universe.service

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_discovery_from_market_universe_v1;")
test "$rows" -gt 0

echo "edge_discovery_rows=$rows"
echo "VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1_OK"
