#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/finam_core/risk/ng_smart_entry_quality_gate_v1.py

python3 - <<'PY'
from finam_core.risk.ng_smart_entry_quality_gate_v1 import NgSmartEntryQualityGateV1

gate = NgSmartEntryQualityGateV1()

cases = [
    ("NG", "smart_entry_retest", "trend_down_high_vol", False, "BLOCK"),
    ("NG", "smart_entry_retest", "trend_up_high_vol", True, "ALLOW"),
    ("NG", "paper_fill_fallback", "trend_down_high_vol", True, "PASS"),
    ("BR", "smart_entry_retest", "trend_down_high_vol", True, "PASS"),
]

for root, entry_reason, regime, expected_allowed, expected_action in cases:
    d = gate.evaluate(root_symbol=root, entry_reason=entry_reason, regime=regime)
    print(
        "NG_SMART_ENTRY_QUALITY_GATE_ROW "
        f"root={root} entry_reason={entry_reason} regime={regime} "
        f"allowed={int(d.allowed)} action={d.action} reason={d.reason}"
    )
    assert d.allowed is expected_allowed
    assert d.action == expected_action

print("NG_SMART_ENTRY_QUALITY_GATE_V1_OK")
PY

echo "TEST_NG_SMART_ENTRY_QUALITY_GATE_V1_OK"
