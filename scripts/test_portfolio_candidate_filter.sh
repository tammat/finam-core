#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.data.portfolio_candidate_filter import PortfolioAwareCandidateFilter

f = PortfolioAwareCandidateFilter()

positions = {
    "SBER@MISX": {"qty": 10},
    "GAZP@MISX": {"qty": -5},
}

rows = [
    {"symbol": "SBER@MISX", "direction": "GAINER"},
    {"symbol": "SBER@MISX", "direction": "LOSER"},
    {"symbol": "GAZP@MISX", "direction": "LOSER"},
    {"symbol": "YDEX@MISX", "direction": "GAINER"},
]

out = f.apply(rows, positions)

assert out[0]["portfolio_status"] == "ALREADY_HELD_LONG"
assert out[0]["portfolio_action"] == "HOLD_OR_ADD_CHECK"

assert out[1]["portfolio_status"] == "ALREADY_HELD_LONG"
assert out[1]["portfolio_action"] == "EXIT_WATCH"

assert out[2]["portfolio_status"] == "ALREADY_HELD_SHORT"
assert out[2]["portfolio_action"] == "HOLD_OR_ADD_CHECK"

assert out[3]["portfolio_status"] == "NEW_CANDIDATE"
assert out[3]["portfolio_action"] == "WATCH_FOR_ENTRY"

print("PORTFOLIO_CANDIDATE_FILTER_OK")
PY
