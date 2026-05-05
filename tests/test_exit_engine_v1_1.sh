#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/exit_engine.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -R "PIPE_EXIT_ENGINE_DUPLICATE_BLOCK" src/finam_core/pipelines/paper_pipeline.py >/dev/null
grep -R "PIPE_EXIT_ENGINE_SM_FILLED" src/finam_core/pipelines/paper_pipeline.py >/dev/null
grep -R "self.exit_state_machine.on_position(symbol, 0.0)" src/finam_core/pipelines/paper_pipeline.py >/dev/null

bash scripts/test_exit_state_machine.sh
bash scripts/test_exit_engine.sh
bash scripts/test_ng_strategy.sh
bash scripts/test_ng_knife.sh

echo "EXIT_ENGINE_V1_1_OK"
