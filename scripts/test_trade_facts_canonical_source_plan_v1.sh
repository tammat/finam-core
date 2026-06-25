#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_TRADE_FACTS_CANONICAL_SOURCE_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_trade_facts_canonical_source_plan_v1.py

src/scripts/research/build_trade_facts_canonical_source_plan_v1.py \
  | tee /tmp/trade_facts_canonical_source_plan_v1.out

grep -q "TRADE_FACTS_CANONICAL_SOURCE_PLAN_V1" /tmp/trade_facts_canonical_source_plan_v1.out
grep -q "canonical_source=public.trade_outcomes" /tmp/trade_facts_canonical_source_plan_v1.out
grep -q "fallback_source=public.closed_trade_chains_v3" /tmp/trade_facts_canonical_source_plan_v1.out
grep -q "reason=research.trade_facts_table_not_exists" /tmp/trade_facts_canonical_source_plan_v1.out
grep -q "MAP target=net_pnl source=public.trade_outcomes.net_pnl" /tmp/trade_facts_canonical_source_plan_v1.out
grep -q "rule=market_state_trade_linker_must_use_existing_canonical_source" /tmp/trade_facts_canonical_source_plan_v1.out
grep -q "VERDICT=TRADE_FACTS_CANONICAL_SOURCE_PLAN_READY" /tmp/trade_facts_canonical_source_plan_v1.out

echo "TEST_TRADE_FACTS_CANONICAL_SOURCE_PLAN_V1_OK"
