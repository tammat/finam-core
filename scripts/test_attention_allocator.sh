#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.portfolio.attention_allocator import AttentionAllocator
from finam_core.data.volatility_scanner import VolatilityCandidate

positions = {
    "SBER@MISX": {"qty": 100, "pnl_pct": 0.015},
    "PLZL@MISX": {"qty": 2, "pnl_pct": -0.01},
    "VTBR@MISX": {"qty": -400, "pnl_pct": 0.005},
    "OLD@MISX": {"qty": 10, "pnl_pct": -0.03},
}

candidates = [
    VolatilityCandidate("SBER@MISX", "intraday", 3.4, 0, 0.025, 2_000_000_000, 2, 0.2, 0.01, "trend_up", "passed"),
    VolatilityCandidate("PLZL@MISX", "intraday", 3.2, 0, 0.025, 2_000_000_000, 2, 0.2, -0.01, "trend_down", "passed"),
    VolatilityCandidate("VTBR@MISX", "intraday", 3.1, 0, 0.02, 1_000_000_000, 2, 0.2, 0.01, "trend_up", "passed"),
    VolatilityCandidate("X5@MISX", "intraday", 4.2, 0, 0.03, 1_000_000_000, 3, 0.3, 0.015, "trend_up", "passed"),
]

allocator = AttentionAllocator(high_score=3.0, rotation_score_gap=0.5)
decisions = allocator.allocate_attention(positions=positions, candidates=candidates, max_active_symbols=10)
by_symbol = {d.symbol: d for d in decisions}

assert by_symbol["SBER@MISX"].action == "ADD_CANDIDATE", by_symbol["SBER@MISX"]
assert by_symbol["PLZL@MISX"].action == "REDUCE", by_symbol["PLZL@MISX"]
assert by_symbol["VTBR@MISX"].action == "REDUCE", by_symbol["VTBR@MISX"]
assert by_symbol["OLD@MISX"].action == "TIGHTEN_STOP", by_symbol["OLD@MISX"]
assert by_symbol["X5@MISX"].action == "ROTATION_CANDIDATE", by_symbol["X5@MISX"]
assert decisions[0].priority >= decisions[-1].priority, decisions

print("ATTENTION_ALLOCATOR_OK")
PY
