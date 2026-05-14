#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/signal_router.py \
  src/finam_core/risk/risk_router.py \
  src/finam_core/pipelines/pipeline_kernel.py \
  src/finam_core/execution/execution_gateway.py \
  src/finam_core/pipelines/paper_pipeline.py

./scripts/test_signal_router_compile.sh
./scripts/test_risk_router_compile.sh
./scripts/test_pipeline_kernel_compile.sh
./scripts/test_execution_gateway_compile.sh

echo "OK: extracted layers regression compile"
