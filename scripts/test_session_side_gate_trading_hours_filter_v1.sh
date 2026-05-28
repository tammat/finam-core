#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_SESSION_SIDE_GATE_TRADING_HOURS_FILTER_V1_START"

python -m py_compile \
  src/scripts/analytics/build_session_side_gate_trading_hours_filter_v1.py \
  src/finam_core/execution/runtime_edge_governance_soft_block_v1.py \
  src/finam_core/execution/session_side_execution_gate_v1.py \
  src/finam_core/execution/edge_gate_strict_mode_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
import json
from pathlib import Path

cfg = json.loads(Path("runtime/session_side_execution_gate_v1.json").read_text(encoding="utf-8"))

allow_buy = [
    row for row in cfg.get("allow", [])
    if row.get("symbol") == "BR_ROLLING@RTSX"
    and row.get("entry_side") == "BUY"
]

hours = sorted(int(row["hour_msk"]) for row in allow_buy)

print("TRADING_HOURS_ALLOW_BUY_HOURS", hours)

assert 8 not in hours, hours
assert 10 in hours, hours

print("SESSION_SIDE_GATE_TRADING_HOURS_CONFIG_OK")
PY

./scripts/test_phase2_soft_block_runtime_smoke_v1.sh
./scripts/test_runtime_edge_governance_phase2_soft_block_v1.sh
./scripts/test_edge_gate_strict_mode_candidate_v1.sh
./scripts/test_edge_gate_pnl_decay_monitor_v1.sh

python src/scripts/analytics/build_edge_gate_decay_final_check_v1.py
python src/scripts/analytics/build_edge_gate_runtime_rollout_check_v1.py
python src/scripts/analytics/build_phase2_soft_block_pipeline_final_check_v1.py
python src/scripts/analytics/build_phase2_soft_block_runtime_smoke_v1.py

echo "TEST_SESSION_SIDE_GATE_TRADING_HOURS_FILTER_V1_OK"
