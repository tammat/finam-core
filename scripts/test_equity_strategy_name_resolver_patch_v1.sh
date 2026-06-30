#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_STRATEGY_NAME_RESOLVER_PATCH_V1 ==="

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "def _strategy_name_for_symbol(self, symbol: str, \*, _allow_equity_runtime: bool = True)" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "Для @MISX приоритет — runtime_active_universe.strategy" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "_allow_equity_runtime=False" \
  src/finam_core/pipelines/paper_pipeline.py

python3 src/scripts/runtime/build_equity_strategy_name_resolver_patch_plan_v1.py \
  | tee /tmp/equity_strategy_name_resolver_patch_v1_plan_check.log

grep -q "VERDICT=EQUITY_STRATEGY_NAME_RESOLVER_PATCH_PLAN_READY" \
  /tmp/equity_strategy_name_resolver_patch_v1_plan_check.log

echo "VERDICT=EQUITY_STRATEGY_NAME_RESOLVER_PATCH_OK"
echo "TEST_EQUITY_STRATEGY_NAME_RESOLVER_PATCH_V1_OK"
