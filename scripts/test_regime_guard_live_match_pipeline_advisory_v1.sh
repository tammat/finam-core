#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/regime_guard_advisory_service.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_REGIME_GUARD_ADVISORY" src/finam_core/pipelines/paper_pipeline.py
grep -q "actual_block=0" src/finam_core/pipelines/paper_pipeline.py
grep -q "advisory_only=1" src/finam_core/pipelines/paper_pipeline.py
grep -q "regime_guard_live_match_pipeline_advisory_v1" src/finam_core/pipelines/paper_pipeline.py

python3 - <<'PY'
from finam_core.governance.regime_guard_advisory_service import RegimeGuardAdvisoryService

d = RegimeGuardAdvisoryService().evaluate()
print(
    f"REGIME_ADVISORY_DECISION scope={d.scope} key={d.regime_key} "
    f"matched={int(d.matched)} classification={d.classification} "
    f"would_block={int(d.would_block)} actual_block=0 advisory_only=1"
)
PY

echo REGIME_GUARD_LIVE_MATCH_PIPELINE_ADVISORY_V1_OK
