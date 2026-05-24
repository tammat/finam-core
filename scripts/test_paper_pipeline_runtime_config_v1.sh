#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/config/runtime_config.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RuntimeConfig" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q 'runtime_config.get("EXECUTION_MODE"' \
  src/finam_core/pipelines/paper_pipeline.py

grep -q 'runtime_config.get_bool("ENABLE_PAPER_FILLS"' \
  src/finam_core/pipelines/paper_pipeline.py

grep -q 'runtime_config.get_bool("SIMULATE_MARKET"' \
  src/finam_core/pipelines/paper_pipeline.py

if grep -q 'os.getenv("EXECUTION_MODE"' \
  src/finam_core/pipelines/paper_pipeline.py; then
    echo "DIRECT_EXECUTION_MODE_GETENV_STILL_PRESENT"
    exit 1
fi

if grep -q 'os.getenv("ENABLE_PAPER_FILLS"' \
  src/finam_core/pipelines/paper_pipeline.py; then
    echo "DIRECT_ENABLE_PAPER_FILLS_GETENV_STILL_PRESENT"
    exit 1
fi

if grep -q 'os.getenv("SIMULATE_MARKET"' \
  src/finam_core/pipelines/paper_pipeline.py; then
    echo "DIRECT_SIMULATE_MARKET_GETENV_STILL_PRESENT"
    exit 1
fi

echo "PAPER_PIPELINE_RUNTIME_CONFIG_V1_OK"
