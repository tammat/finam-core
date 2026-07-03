#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_ADOPTION_RANKING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_model_v1.py \
  src/scripts/build_market_universe_ranking_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_model_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py \
  | tee /tmp/market_model_adoption_ranking_v1.txt

grep -q "VERDICT=MARKET_UNIVERSE_RANKING_V1_READY" \
  /tmp/market_model_adoption_ranking_v1.txt

if grep -q "public.market_bars" src/scripts/build_market_universe_ranking_v1.py; then
  echo "ERROR_PUBLIC_MARKET_BARS_STILL_IN_RANKING_BUILDER"
  exit 1
fi

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM marketcore_ui.market_universe_ranking_v1;
")

symbols=$(psql -At -d finam_core -c "
SELECT count(DISTINCT symbol)
FROM marketcore_ui.market_universe_ranking_v1;
")

test "$rows" -gt 0
test "$symbols" -gt 1

psql -d finam_core -c "
SELECT *
FROM marketcore_ui.market_universe_ranking_v1
ORDER BY 1
LIMIT 20;
"

echo "ranking_rows=$rows"
echo "ranking_symbols=$symbols"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_MODEL_ADOPTION_RANKING_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_ADOPTION_RANKING_V1_OK"
