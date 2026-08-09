#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST EDGE ASSET STRATEGY DECISION BOARD V1 ==="

python -m py_compile \
  src/marketcore/presentation/workspace_v2/edge_asset_strategy_decision_board_v1.py \
  src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py

echo
echo "=== INTEGRATION ==="

grep -q \
  'render_edge_asset_strategy_decision_board_v1' \
  src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py

grep -q \
  'asset_strategy_decision_board = render_edge_asset_strategy_decision_board_v1()' \
  src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py

grep -q \
  '{asset_strategy_decision_board}' \
  src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py

echo
echo "=== BOARD RENDER ==="

OUTPUT="$(
PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.edge_asset_strategy_decision_board_v1 import (
    render_edge_asset_strategy_decision_board_v1,
)

result = render_edge_asset_strategy_decision_board_v1()

print(result)
PY
)"

echo "$OUTPUT"

grep -q 'Решения по инструментам и стратегиям' <<< "$OUTPUT"
grep -q 'Золото' <<< "$OUTPUT"
grep -q 'Brent' <<< "$OUTPUT"
grep -q 'Природный газ' <<< "$OUTPUT"
grep -q 'GOLD_UP_REGIME_FROZEN_V1' <<< "$OUTPUT"
grep -q 'BR_CONSERVATIVE_BREAKOUT' <<< "$OUTPUT"
grep -q 'RESEARCH_ACTIVE' <<< "$OUTPUT"

echo
echo "=== SAFETY ==="
git diff --check
git status --short

echo
echo "VERDICT=TEST_EDGE_ASSET_STRATEGY_DECISION_BOARD_V1_OK"

echo
echo "=== NEXT ACTION CONTRACT ==="

grep -q \
  'Следующее действие' \
  <<< "$OUTPUT"

grep -q \
  'Накопить prospective OOS: 0/20' \
  <<< "$OUTPUT"

grep -q \
  'Понизить приоритет BR; искать edge в других инструментах' \
  <<< "$OUTPUT"

grep -q \
  'Искать новую независимую гипотезу' \
  <<< "$OUTPUT"

echo "VERDICT=TEST_EDGE_DECISION_BOARD_NEXT_ACTION_V1_OK"
