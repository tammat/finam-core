#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_PAYLOAD_V2_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "def _build_runtime_governance_explainability_payload_v2(" src/finam_core/pipelines/paper_pipeline.py
grep -q "runtime_governance_explainability_payload_v2" src/finam_core/pipelines/paper_pipeline.py
grep -q '"уровень_уверенности"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"сила_преимущества"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"доказательства"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"причина"' src/finam_core/pipelines/paper_pipeline.py

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_PAYLOAD_V2_OK"
