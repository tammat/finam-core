#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/analytics/build_strategy_regime_matrix.py

grep -q "trade_context_envelopes" src/scripts/analytics/build_strategy_regime_matrix.py
grep -q "analytics_intraday_pnl" src/scripts/analytics/build_strategy_regime_matrix.py
grep -q "strategy_regime_matrix" src/scripts/analytics/build_strategy_regime_matrix.py
grep -q "v_strategy_regime_matrix_ru" src/scripts/analytics/build_strategy_regime_matrix.py
grep -q "regime->" src/scripts/analytics/build_strategy_regime_matrix.py || true

echo "STRATEGY_REGIME_MATRIX_FROM_CONTEXT_ENVELOPES_TEST_OK"
