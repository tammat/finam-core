#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/research/historical_replay_research_v1.py

grep -q "market_bars" src/scripts/research/historical_replay_research_v1.py
grep -q "build_intraday_pnl.py" src/scripts/research/historical_replay_research_v1.py
grep -q "build_regime_snapshots_v2.py" src/scripts/research/historical_replay_research_v1.py
grep -q "build_trade_context_envelopes.py" src/scripts/research/historical_replay_research_v1.py
grep -q "build_regime_aware_edge_v1.py" src/scripts/research/historical_replay_research_v1.py
grep -q "build_edge_validation_table.py" src/scripts/research/historical_replay_research_v1.py

echo "HISTORICAL_REPLAY_RESEARCH_V1_TEST_OK"
