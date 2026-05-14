#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/execution_gateway.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "class ExecutionGateway" src/finam_core/execution/execution_gateway.py
grep -q "ExecutionGatewayInput" src/finam_core/execution/execution_gateway.py
grep -q "self.execution_gateway = ExecutionGateway(self)" src/finam_core/pipelines/paper_pipeline.py

echo "OK: execution gateway compile"
