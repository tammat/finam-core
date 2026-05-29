#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_PAYLOAD_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "def _build_runtime_governance_explainability_payload_v1(" src/finam_core/pipelines/paper_pipeline.py
grep -q '"explainability": self._build_runtime_governance_explainability_payload_v1(phase2_decision)' src/finam_core/pipelines/paper_pipeline.py
grep -q "основание_решения" src/finam_core/pipelines/paper_pipeline.py
grep -q "статус_выборки" src/finam_core/pipelines/paper_pipeline.py
grep -q "runtime_governance_explainability_payload_v1" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_PAYLOAD_V1_OK"
