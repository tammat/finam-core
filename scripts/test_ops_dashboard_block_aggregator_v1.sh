#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_OPS_DASHBOARD_BLOCK_AGGREGATOR_V1_START"

bash -n scripts/ops/finam_ops.sh

grep -q "БЛОКИРОВКИ СИГНАЛОВ ЗА 30 МИНУТ" scripts/ops/finam_ops.sh
grep -q "RUNTIME_GUARD_PRE_SIGNAL_BLOCK_SAVED" scripts/ops/finam_ops.sh
grep -q "ПОСЛЕДНИЕ FILL BR/NG ЗА 1 ЧАС" scripts/ops/finam_ops.sh
grep -q "BRN6@RTSX" scripts/ops/finam_ops.sh
grep -q "NGN6@RTSX" scripts/ops/finam_ops.sh

echo "TEST_OPS_DASHBOARD_BLOCK_AGGREGATOR_V1_OK"
