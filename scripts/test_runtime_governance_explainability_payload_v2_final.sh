#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_PAYLOAD_V2_FINAL_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q '"вердикт"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"человеческое_объяснение"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"уровень_доверия"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"источник_решения"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"предполагаемый_результат_без_блокировки"' src/finam_core/pipelines/paper_pipeline.py
grep -q "ВХОД ЗАПРЕЩЕН" src/finam_core/pipelines/paper_pipeline.py
grep -q "ВХОД РАЗРЕШЕН" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_RUNTIME_GOVERNANCE_EXPLAINABILITY_PAYLOAD_V2_FINAL_OK"
