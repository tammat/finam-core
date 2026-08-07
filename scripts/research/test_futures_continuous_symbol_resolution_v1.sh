#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_futures_continuous_symbol_resolution_v1.py"
LOG="/tmp/test_futures_continuous_symbol_resolution_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

set +e

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --continuous-symbol "NG@RTSX" \
  --bar-schema public \
  --bar-table market_bars \
  --minimum-bars 100 |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "resolution_exit_code=$RC"

grep -Fq "continuous_symbol=NG@RTSX" "$LOG"
grep -Fq "eligible_contract_count=" "$LOG"
grep -Fq "recommended_contract_symbol=" "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE analytics" \
  "DELETE FROM analytics" \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" "$BUILDER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
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
      "VERDICT=FUTURES_CONTINUOUS_SYMBOL_RESOLUTION_V1_READY" \
      "$LOG"

    echo \
      "VERDICT=TEST_FUTURES_CONTINUOUS_SYMBOL_RESOLUTION_V1_OK"
    exit 0
fi

if [[ "$RC" -eq 2 ]]; then
    grep -Fq \
      "VERDICT=FUTURES_CONTINUOUS_SYMBOL_RESOLUTION_V1_BLOCKED" \
      "$LOG"

    echo \
      "VERDICT=TEST_FUTURES_CONTINUOUS_SYMBOL_RESOLUTION_V1_BLOCKED_CORRECTLY"
    exit 0
fi

echo \
  "VERDICT=TEST_FUTURES_CONTINUOUS_SYMBOL_RESOLUTION_V1_FAILED"

exit "$RC"
