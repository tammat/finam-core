#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/risk/risk_router.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "class RiskRouter" src/finam_core/risk/risk_router.py
grep -q "RiskRouteInput" src/finam_core/pipelines/paper_pipeline.py
grep -q "self.risk_router = RiskRouter(self)" src/finam_core/pipelines/paper_pipeline.py
grep -q "risk_router.route" src/finam_core/pipelines/paper_pipeline.py

echo "OK: risk router compile"
