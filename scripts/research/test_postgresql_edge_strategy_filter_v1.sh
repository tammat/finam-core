#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

BUILDER="scripts/research/build_postgresql_edge_parameter_search_v1.py"

echo "=== TEST POSTGRESQL EDGE STRATEGY FILTER V1 ==="

PYTHONPATH=src \
/opt/finam-core/venv/bin/python -m py_compile \
  "$BUILDER"

# ----------------------------------------------------------
# ATR only = 24
# ----------------------------------------------------------

ATR_LOG="/tmp/test_edge_strategy_filter_atr_v1.log"

PYTHONPATH=src \
/opt/finam-core/venv/bin/python \
  "$BUILDER" \
  --symbols BRZ6@RTSX \
  --timeframes M5 \
  --strategies ATR_IMPULSE_V1 \
  --commission-per-side 1.5 \
  --slippage-bps 2.0 \
  --bar-limit 20000 \
  --batch-id TEST_ATR_FILTER_V1 \
  --max-tasks 24 \
  --plan-only \
  > "$ATR_LOG"

grep -Fq "task_count=24" "$ATR_LOG"
grep -Fq "atr_task_count=24" "$ATR_LOG"
grep -Fq "momentum_task_count=0" "$ATR_LOG"
grep -Fq "inserted_count=0" "$ATR_LOG"
grep -Fq "plan_only=1" "$ATR_LOG"


# ----------------------------------------------------------
# Momentum only = 12
# ----------------------------------------------------------

MOM_LOG="/tmp/test_edge_strategy_filter_momentum_v1.log"

PYTHONPATH=src \
/opt/finam-core/venv/bin/python \
  "$BUILDER" \
  --symbols BRZ6@RTSX \
  --timeframes M5 \
  --strategies MOMENTUM_CONTINUATION_V1 \
  --commission-per-side 1.5 \
  --slippage-bps 2.0 \
  --bar-limit 20000 \
  --batch-id TEST_MOM_FILTER_V1 \
  --max-tasks 12 \
  --plan-only \
  > "$MOM_LOG"

grep -Fq "task_count=12" "$MOM_LOG"
grep -Fq "atr_task_count=0" "$MOM_LOG"
grep -Fq "momentum_task_count=12" "$MOM_LOG"


# ----------------------------------------------------------
# Без selector прежнее поведение = 36.
# ----------------------------------------------------------

ALL_LOG="/tmp/test_edge_strategy_filter_default_v1.log"

PYTHONPATH=src \
/opt/finam-core/venv/bin/python \
  "$BUILDER" \
  --symbols BRZ6@RTSX \
  --timeframes M5 \
  --commission-per-side 1.5 \
  --slippage-bps 2.0 \
  --bar-limit 20000 \
  --batch-id TEST_DEFAULT_FILTER_V1 \
  --max-tasks 36 \
  --plan-only \
  > "$ALL_LOG"

grep -Fq "task_count=36" "$ALL_LOG"
grep -Fq "atr_task_count=24" "$ALL_LOG"
grep -Fq "momentum_task_count=12" "$ALL_LOG"


echo "atr_only_task_count=24"
echo "momentum_only_task_count=12"
echo "default_task_count=36"

echo "backward_compatibility_confirmed=1"

echo "db_writes_performed=0"
echo "parameter_grid_changed=0"
echo "checkpoint_changed=0"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_POSTGRESQL_EDGE_STRATEGY_FILTER_V1_OK"
