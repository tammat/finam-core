#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GATE_LIVE_DECISION_PROBE_V1_START"

python -m py_compile \
  src/finam_core/execution/session_side_execution_gate_v1.py \
  src/finam_core/execution/session_side_gate_runtime_audit_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo

from finam_core.execution.session_side_execution_gate_v1 import SessionSideExecutionGateV1

print("RUNTIME_GATE_LIVE_DECISION_PROBE_V1")

gate = SessionSideExecutionGateV1("runtime/session_side_execution_gate_v1.json")

now_msk = datetime.now(tz=ZoneInfo("Europe/Moscow"))

for symbol in ("BRN6@RTSX", "BR_ROLLING@RTSX"):
    for side in ("BUY", "SELL"):
        decision = gate.decide(
            symbol=symbol,
            side=side,
            ts=now_msk,
        )

        print(
            "RUNTIME_GATE_LIVE_DECISION_PROBE_ROW",
            f"symbol={decision.symbol}",
            f"side={decision.side}",
            f"hour_msk={decision.hour_msk}",
            f"session={decision.session_name}",
            f"action={decision.action}",
            f"allowed={decision.allowed}",
            f"reason={decision.reason}",
            f"matched_symbol={decision.matched_symbol}",
            f"expectancy={decision.expectancy_points}",
            f"closed_trades={decision.closed_trades}",
        )

print("RUNTIME_GATE_LIVE_DECISION_PROBE_V1_OK")
PY

python src/scripts/analytics/build_session_side_gate_final_healthcheck_v1.py

echo "TEST_RUNTIME_GATE_LIVE_DECISION_PROBE_V1_OK"
