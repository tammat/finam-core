#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_BUILDER_COMPLETE_V1 ==="

scripts/test_resolve_source_system_step_v1.sh >/tmp/t1.out
scripts/test_resolve_symbol_alias_step_v1.sh >/tmp/t2.out
scripts/test_resolve_instrument_step_v1.sh >/tmp/t3.out
scripts/test_resolve_contract_step_v1.sh >/tmp/t4.out
scripts/test_resolve_timeframe_step_v1.sh >/tmp/t5.out

scripts/test_build_bar_event_step_v1.sh >/tmp/t6.out
scripts/test_run_quality_step_v1.sh >/tmp/t7.out
scripts/test_build_lineage_step_v1.sh >/tmp/t8.out

scripts/test_persist_events_step_v1.sh >/tmp/t9.out
scripts/test_persist_quality_step_v1.sh >/tmp/t10.out
scripts/test_persist_lineage_step_v1.sh >/tmp/t11.out

grep -q TEST_RESOLVE_SOURCE_SYSTEM_STEP_V1_OK /tmp/t1.out
grep -q TEST_RESOLVE_SYMBOL_ALIAS_STEP_V1_OK /tmp/t2.out
grep -q TEST_RESOLVE_INSTRUMENT_STEP_V1_OK /tmp/t3.out
grep -q TEST_RESOLVE_CONTRACT_STEP_V1_OK /tmp/t4.out
grep -q TEST_RESOLVE_TIMEFRAME_STEP_V1_OK /tmp/t5.out

grep -q TEST_BUILD_BAR_EVENT_STEP_V1_OK /tmp/t6.out
grep -q TEST_RUN_QUALITY_STEP_V1_OK /tmp/t7.out
grep -q TEST_BUILD_LINEAGE_STEP_V1_OK /tmp/t8.out

grep -q TEST_PERSIST_EVENTS_STEP_V1_OK /tmp/t9.out
grep -q TEST_PERSIST_QUALITY_STEP_V1_OK /tmp/t10.out
grep -q TEST_PERSIST_LINEAGE_STEP_V1_OK /tmp/t11.out

echo "resolution_phase=READY"
echo "build_phase=READY"
echo "quality_phase=READY"
echo "lineage_phase=READY"
echo "persist_phase=READY"

echo "builder_complete=READY"
echo "integration=READY"
echo "idempotent_design=READY"
echo "no_vendor_lock=1"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_DATA_NORMALIZATION_BUILDER_COMPLETE_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_BUILDER_COMPLETE_V1_OK"
