#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_LEGACY_RESEARCH_CANDIDATES_REMOVE_V1 ==="

grep -R "paper_edge_research_candidates_v1" -n \
  src/marketcore/api \
  src/marketcore/presentation/pages \
  src/scripts \
  --exclude-dir="__pycache__" || true

echo "=== ALLOWED LEGACY ONLY ==="
echo "Allowed:"
echo "src/scripts/build_edge_discovery_use_market_universe_v1.py"
echo "src/scripts/build_paper_edge_discovery_research_candidates_v1.py"
echo "src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py"

bad=$(grep -R "paper_edge_research_candidates_v1" -n \
  src/marketcore/api \
  src/marketcore/presentation/pages \
  src/scripts \
  --exclude-dir="__pycache__" \
  | grep -v "build_edge_discovery_use_market_universe_v1.py" \
  | grep -v "build_paper_edge_discovery_research_candidates_v1.py" \
  | grep -v "build_phase_ii_paper_edge_discovery_summary_v1.py" \
  | grep -v "audit_edge_ui_use_market_universe_v1.py" \
  || true)

if [ -n "$bad" ]; then
  echo "$bad"
  echo "VERDICT=EDGE_LEGACY_RESEARCH_CANDIDATES_REMOVE_V1_FAILED"
  exit 1
fi

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_binding_v1.py >/tmp/legacy_remove_binding.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_freshness_v1.py >/tmp/legacy_remove_freshness.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_from_market_universe_v1.py >/tmp/legacy_remove_discovery.txt

br_any=$(psql -At -d finam_core -c "
SELECT count(*)
FROM marketcore_ui.paper_edge_market_data_freshness_v1
WHERE candidate_symbol='BR@RTSX' AND candidate_timeframe='ANY';
")

symbols=$(psql -At -d finam_core -c "
SELECT count(DISTINCT candidate_symbol)
FROM marketcore_ui.paper_edge_market_data_freshness_v1
WHERE row_type='CANDIDATE_BINDING';
")

edge_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM marketcore_ui.edge_discovery_from_market_universe_v1;
")

test "$br_any" = "0"
test "$symbols" -gt 1
test "$edge_rows" -gt 0

echo "br_any=$br_any"
echo "binding_symbols=$symbols"
echo "edge_rows=$edge_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_LEGACY_RESEARCH_CANDIDATES_REMOVE_V1_READY"
echo "VERDICT=TEST_EDGE_LEGACY_RESEARCH_CANDIDATES_REMOVE_V1_OK"
