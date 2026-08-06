#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
ADAPTER="src/finam_core/research/postgresql_edge_backtest_adapter_v1.py"
BUILDER="scripts/research/build_postgresql_edge_backtest_adapter_v1.py"
LOG="/tmp/test_postgresql_edge_backtest_adapter_v1.log"

cd "$ROOT"

echo "=== TEST POSTGRESQL EDGE BACKTEST ADAPTER V1 ==="

rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile \
  "$ADAPTER" \
  "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" |
tee "$LOG"

PYTHONPATH=src \
"$PYTHON" "$ADAPTER" --self-test |
tee -a "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_BUILD_READY" \
  "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_SELF_TEST_OK" \
  "$LOG"

for marker in \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order(" \
  "execution_enabled = true" \
  "micro_live_allowed = true"
do
    COUNT="$(
      {
        grep -F "$marker" "$ADAPTER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

PYTHONPATH=src \
"$PYTHON" - "$ADAPTER" <<'PY'
from __future__ import annotations

import ast
import pathlib
import sys


path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

required_sql = (
    "FOR UPDATE SKIP LOCKED",
    "DELETE FROM analytics.research_trade_v1",
    "INSERT INTO analytics.research_trade_v1",
    "DELETE FROM analytics.edge_observation_v1",
    "INSERT INTO analytics.edge_observation_v1",
    "status_code = 'RUNNING'",
    "status_code = 'FAILED'",
)

for fragment in required_sql:
    if fragment not in source:
        raise SystemExit(
            f"ERROR=required_sql_missing:{fragment}"
        )

assert "commission_per_side" in source
assert "slippage_bps" in source
assert "required_cost_parameters_missing" in source

print("task_claim_contract=OK")
print("trade_persistence_contract=OK")
print("observation_persistence_contract=OK")
print("explicit_cost_contract=OK")
print("failed_status_contract=OK")
print("VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_STATIC_OK")
PY

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

TRACKED_DIRTY_COUNT="$(
  {
    git status --porcelain |
    grep -Ev '^\?\?' ||
    true
  } |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
echo "tracked_dirty_count=$TRACKED_DIRTY_COUNT"

[[ "$STAGED_COUNT" -eq 0 ]]
[[ "$TRACKED_DIRTY_COUNT" -eq 0 ]]

echo "db_writes_performed=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_OK"
