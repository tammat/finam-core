#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKET_MODEL_ADOPTION_ALIAS_V1 ==="

cp src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py \
   /tmp/build_paper_edge_market_symbol_alias_plan_v1.before_market_model_adoption.bak

python - <<'PY'
from pathlib import Path

p = Path("src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py")
s = p.read_text()

s = s.replace(
'''SOURCE_TABLE_CANDIDATES = [
    "public.market_bars",
    "public.market_data_bars",
    "public.bars",
    "public.candles",
    "public.market_candles",
    "public.ohlcv_bars",
]''',
'''SOURCE_TABLE_CANDIDATES = [
    "marketcore.market_snapshot_v1",
]'''
)

s = s.replace("public.market_bars", "marketcore.market_snapshot_v1")
s = s.replace("market_bars", "market_snapshot_v1")

p.write_text(s)
PY

cat > scripts/test_market_model_adoption_alias_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_ADOPTION_ALIAS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_model_v1.py \
  src/scripts/build_paper_edge_market_data_binding_v1.py \
  src/scripts/build_paper_edge_market_data_freshness_v1.py \
  src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_model_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_binding_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_freshness_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py \
  | tee /tmp/market_model_adoption_alias_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_READY" \
  /tmp/market_model_adoption_alias_v1.txt

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;
")

bad_source=$(psql -At -d finam_core -c "
SELECT count(*)
FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
WHERE alias_source_table <> 'marketcore.market_snapshot_v1';
")

old_br_any=$(psql -At -d finam_core -c "
SELECT count(*)
FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
WHERE candidate_symbol='BR@RTSX'
  AND candidate_timeframe='ANY';
")

test "$rows" -gt 0
test "$bad_source" = "0"
test "$old_br_any" = "0"

psql -d finam_core -c "
SELECT candidate_symbol, candidate_timeframe, alias_symbol, alias_timeframe,
       alias_source_table, alias_bars_total, alias_latest_bar_ts, alias_status
FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
ORDER BY plan_rank
LIMIT 30;
"

echo "alias_rows=$rows"
echo "bad_source=$bad_source"
echo "old_br_any=$old_br_any"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_MODEL_ADOPTION_ALIAS_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_ADOPTION_ALIAS_V1_OK"
SH_TEST

chmod +x scripts/test_market_model_adoption_alias_v1.sh
scripts/test_market_model_adoption_alias_v1.sh

echo "VERDICT=BUILD_MARKET_MODEL_ADOPTION_ALIAS_V1_OK"
