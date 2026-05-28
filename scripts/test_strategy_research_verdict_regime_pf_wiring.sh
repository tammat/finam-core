#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/finam_core/research/research_verdict_repository.py

grep -q "FROM strategy_regime_matrix" src/finam_core/research/research_verdict_repository.py
grep -q "COALESCE(r.regime, p.regime) AS regime" src/finam_core/research/research_verdict_repository.py
grep -q "COALESCE(r.profit_factor, 0)::float AS regime_pf" src/finam_core/research/research_verdict_repository.py

if grep -q "FROM strategy_regime_performance" src/finam_core/research/research_verdict_repository.py; then
  echo "ERROR: old strategy_regime_performance source still used"
  exit 1
fi

echo "STRATEGY_RESEARCH_VERDICT_REGIME_PF_WIRING_TEST_OK"
