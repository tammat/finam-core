#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_OPS_DASHBOARD_MARKET_BARS_FRESHNESS_V1_START"

bash -n scripts/ops/finam_ops.sh

grep -q "СВЕЖЕСТЬ БАРОВ BR/NG/USD" scripts/ops/finam_ops.sh
grep -q "lag_min" scripts/ops/finam_ops.sh
grep -q "NGN6@RTSX" scripts/ops/finam_ops.sh

echo "TEST_OPS_DASHBOARD_MARKET_BARS_FRESHNESS_V1_OK"
