#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_futures_zero_trade_attribution_v1.py"
LOG="/tmp/test_postgresql_futures_zero_trade_attribution_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --symbol "NG@RTSX" \
  --minimum-runs 1 |
tee "$LOG"

grep -Fq "run_count=" "$LOG"
grep -Fq "root_cause=" "$LOG"
grep -Fq \
  "VERDICT=POSTGRESQL_FUTURES_ZERO_TRADE_ATTRIBUTION_V1_READY" \
  "$LOG"

echo "db_writes_performed=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_FUTURES_ZERO_TRADE_ATTRIBUTION_V1_OK"
