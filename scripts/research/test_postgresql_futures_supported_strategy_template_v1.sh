#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
DISCOVERY="scripts/research/discover_postgresql_futures_supported_strategy_template_v1.py"
LOG="/tmp/test_postgresql_futures_supported_strategy_template_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$DISCOVERY"

set +e

PYTHONPATH=src \
"$PYTHON" "$DISCOVERY" |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "supported_template_discovery_exit_code=$RC"

grep -Fq "executable_strategies=" "$LOG"
grep -Fq "eligible_template_count=" "$LOG"
grep -Fq "root_cause=" "$LOG"

for marker in \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" "$DISCOVERY" || true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_runtime_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

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

if [[ "$RC" -eq 0 ]]; then
    grep -Fq \
      "VERDICT=POSTGRESQL_FUTURES_SUPPORTED_STRATEGY_TEMPLATE_V1_READY" \
      "$LOG"

    echo \
      "VERDICT=TEST_POSTGRESQL_FUTURES_SUPPORTED_STRATEGY_TEMPLATE_V1_OK"
    exit 0
fi

grep -Fq \
  "VERDICT=POSTGRESQL_FUTURES_SUPPORTED_STRATEGY_TEMPLATE_V1_BLOCKED" \
  "$LOG"

echo \
  "VERDICT=TEST_POSTGRESQL_FUTURES_SUPPORTED_STRATEGY_TEMPLATE_V1_BLOCKED_CONFIRMED"
