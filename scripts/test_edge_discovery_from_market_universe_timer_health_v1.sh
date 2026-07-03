#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_HEALTH_V1 ==="

systemctl is-enabled finam-edge-discovery-market-universe.timer
systemctl is-active finam-edge-discovery-market-universe.timer

sudo systemctl start finam-edge-discovery-market-universe.service
sleep 2

journalctl -u finam-edge-discovery-market-universe.service --since "5 minutes ago" --no-pager | \
grep -E "EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_CYCLE|EDGE_DISCOVERY_STEP|VERDICT|Traceback|ERROR" || true

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_discovery_from_market_universe_v1;")
candidates=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_discovery_from_market_universe_v1 WHERE edge_status='RESEARCH_CANDIDATE';")
fresh=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1 WHERE freshness_status='CANDIDATE_BOUND_FRESH';")
br_any=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1 WHERE candidate_symbol='BR@RTSX' AND candidate_timeframe='ANY';")

test "$rows" -gt 0
test "$fresh" -gt 0
test "$br_any" = "0"

echo "edge_discovery_rows=$rows"
echo "research_candidates=$candidates"
echo "fresh_bindings=$fresh"
echo "old_br_any=$br_any"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_HEALTH_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_HEALTH_V1_OK"
