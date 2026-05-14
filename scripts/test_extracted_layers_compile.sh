#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/signal_router.py \
  src/finam_core/risk/risk_router.py \
  src/finam_core/pipelines/pipeline_kernel.py \
  src/finam_core/execution/execution_gateway.py \
  src/finam_core/engine/trading_engine_coordinator.py \
  src/finam_core/pipelines/paper_pipeline.py

./scripts/test_signal_router_compile.sh
./scripts/test_risk_router_compile.sh
./scripts/test_pipeline_kernel_compile.sh
./scripts/test_execution_gateway_compile.sh
./scripts/test_trading_engine_coordinator.sh
./scripts/test_engine_coordinator_full_smoke.sh
./scripts/test_engine_coordinator_master_recovery_hook.sh

echo "OK: extracted layers regression compile"
