#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

python3 - <<'PY'
from finam_core.pipelines.paper_pipeline import _ng_short_block_pipeline_hook_v1

assert _ng_short_block_pipeline_hook_v1(symbol="NGN6@RTSX", side="SELL", position=1, quantity=1) is True
assert _ng_short_block_pipeline_hook_v1(symbol="NGN6@RTSX", side="SELL", position=0, quantity=1) is False
assert _ng_short_block_pipeline_hook_v1(symbol="NGN6@RTSX", side="SELL", position=-1, quantity=1) is False
assert _ng_short_block_pipeline_hook_v1(symbol="NGN6@RTSX", side="BUY", position=0, quantity=1) is True
assert _ng_short_block_pipeline_hook_v1(symbol="BRN6@RTSX", side="SELL", position=0, quantity=1) is True

print("NG_SHORT_BLOCK_PIPELINE_HOOK_V1_OK")
PY
