#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE TREND PULLBACK CANONICAL ADAPTER SCREEN V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_trend_pullback_canonical_adapter_screen_v1.py

echo
echo "=== SOURCE CONTRACT ==="

PYTHONPATH=src python - <<'PYGUARD'
import ast
from pathlib import Path

path = Path(
    "src/scripts/research/"
    "build_universe_trend_pullback_canonical_adapter_screen_v1.py"
)

tree = ast.parse(path.read_text())

for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            if (
                "build_strategy_execution_runner_v1"
                in alias.name
            ):
                raise SystemExit(
                    "ERROR=GENERIC_RUNNER_IMPORT_FOUND"
                )

    if isinstance(node, ast.ImportFrom):
        module = node.module or ""

        if (
            "build_strategy_execution_runner_v1"
            in module
        ):
            raise SystemExit(
                "ERROR=GENERIC_RUNNER_IMPORT_FOUND"
            )

print(
    "VERDICT="
    "TREND_PULLBACK_NO_GENERIC_RUNNER_IMPORT_OK"
)
PYGUARD

grep -q \
  'postgresql_edge_backtest_adapter_v1' \
  src/scripts/research/build_universe_trend_pullback_canonical_adapter_screen_v1.py

grep -q \
  'trend_pullback_signal' \
  src/scripts/research/build_universe_trend_pullback_canonical_adapter_screen_v1.py

grep -q \
  'pullback_atr_multiplier' \
  config/research/universe_trend_pullback_canonical_adapter_screen_v1.json

echo \
"VERDICT=TREND_PULLBACK_CANONICAL_SOURCE_CONTRACT_OK"

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_trend_pullback_canonical_adapter_screen_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=canonical_true_gross_signal_screen' \
  <<< "$OUTPUT"

grep -q \
  'canonical_adapter_used=1' \
  <<< "$OUTPUT"

grep -q \
  'generic_execution_runner_used=0' \
  <<< "$OUTPUT"

grep -q \
  'signal_metric_source=GROSS_PNL' \
  <<< "$OUTPUT"

grep -q \
  'parameter_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'execution_costs_used=0' \
  <<< "$OUTPUT"

grep -q \
  'db_writes_performed=0' \
  <<< "$OUTPUT"

grep -q 'runtime_changed=0' \
  <<< "$OUTPUT"

grep -q 'execution_changed=0' \
  <<< "$OUTPUT"

grep -q 'orders_changed=0' \
  <<< "$OUTPUT"

grep -q 'fills_changed=0' \
  <<< "$OUTPUT"

grep -q 'micro_live_allowed=0' \
  <<< "$OUTPUT"

grep -Eq \
'VERDICT=UNIVERSE_TREND_PULLBACK_CANONICAL_(CANDIDATES_FOUND|NO_CANDIDATES)' \
<<< "$OUTPUT"

echo
echo "=== PARAMETER SENSITIVITY CONTRACT ==="

# Разные frozen variants должны реально передаваться
# canonical signal implementation.
for variant in 1 2 3
do
    grep -q \
      "SCREEN_ROW .*variant=${variant} " \
      <<< "$OUTPUT"
done

echo \
"VERDICT=TREND_PULLBACK_CANONICAL_PARAMETER_CONTRACT_OK"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_TREND_PULLBACK_CANONICAL_ADAPTER_SCREEN_V1_OK"
