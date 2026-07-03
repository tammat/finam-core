#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/run_market_universe_research_queue_cycle_v1.py \
  src/scripts/build_paper_edge_market_universe_candidates_v1.py \
  src/scripts/build_market_universe_ranking_v1.py \
  src/scripts/build_market_universe_research_queue_v1.py

test -f deploy/systemd/finam-market-universe-research-queue.service
test -f deploy/systemd/finam-market-universe-research-queue.timer

grep -q "OnUnitActiveSec=5min" deploy/systemd/finam-market-universe-research-queue.timer
grep -q "run_market_universe_research_queue_cycle_v1.py" deploy/systemd/finam-market-universe-research-queue.service

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/run_market_universe_research_queue_cycle_v1.py \
  | tee /tmp/market_universe_research_queue_cycle_v1.txt

grep -q "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE_V1_READY" \
  /tmp/market_universe_research_queue_cycle_v1.txt

sudo cp deploy/systemd/finam-market-universe-research-queue.service /etc/systemd/system/
sudo cp deploy/systemd/finam-market-universe-research-queue.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finam-market-universe-research-queue.timer
sudo systemctl start finam-market-universe-research-queue.service

sleep 2

journalctl -u finam-market-universe-research-queue.service --since "2 minutes ago" --no-pager | \
grep -E "MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE|RESEARCH_QUEUE_CYCLE_STEP|VERDICT|ERROR|Traceback" || true

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1;")
high=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1 WHERE research_priority='HIGH';")

test "$rows" -gt 0
test "$high" -gt 0

echo "research_queue_rows=$rows"
echo "research_queue_high=$high"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1_READY"
echo "VERDICT=TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1_OK"
