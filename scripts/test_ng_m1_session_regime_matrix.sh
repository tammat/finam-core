#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_ng_m1_session_regime_matrix.py

grep -q "ng_m1_session_regime_matrix" src/scripts/build_ng_m1_session_regime_matrix.py
grep -q "NG_M1_SESSION_REGIME_MATRIX_SUMMARY" src/scripts/build_ng_m1_session_regime_matrix.py

echo "TEST_NG_M1_SESSION_REGIME_MATRIX_OK"
