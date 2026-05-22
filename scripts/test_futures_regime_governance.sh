#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/futures_regime_governance_repository.py \
  src/scripts/build_futures_regime_governance.py

grep -q "futures_regime_governance" src/finam_core/research/futures_regime_governance_repository.py
grep -q "BLOCK_RUNTIME" src/finam_core/research/futures_regime_governance_repository.py
grep -q "ALLOW_PAPER_RUNTIME_CANDIDATE" src/finam_core/research/futures_regime_governance_repository.py
grep -q "FUTURES_REGIME_GOVERNANCE_SUMMARY" src/scripts/build_futures_regime_governance.py

echo "TEST_FUTURES_REGIME_GOVERNANCE_OK"
