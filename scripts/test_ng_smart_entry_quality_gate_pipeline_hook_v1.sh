#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/risk/ng_smart_entry_quality_gate_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "NgSmartEntryQualityGateV1" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_NG_SMART_ENTRY_QUALITY_GATE_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_SMART_ENTRY_QUALITY_GATE_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_SMART_ENTRY_QUALITY_BLOCK_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "ng_smart_entry_quality_gate_pipeline_hook_v1" src/finam_core/pipelines/paper_pipeline.py

./scripts/test_ng_smart_entry_quality_gate_v1.sh

echo "TEST_NG_SMART_ENTRY_QUALITY_GATE_PIPELINE_HOOK_V1_OK"
