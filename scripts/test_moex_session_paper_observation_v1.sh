#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MOEX_SESSION_PAPER_OBSERVATION_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/run_moex_session_paper_observation_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/run_moex_session_paper_observation_v1.py | tee "$out"

grep -q "TEST_MOEX_SESSION_PAPER_OBSERVATION_V1_OK" "$out"
grep -q "runtime_allow_trading=0" "$out"
grep -q "execution_enabled=0" "$out"
grep -q "real_trading_enabled=0" "$out"
grep -q "equity_session_now=" "$out"
grep -q "futures_session_now=" "$out"
grep -q "moex_session_now=" "$out"

echo "VERDICT=MOEX_SESSION_PAPER_OBSERVATION_TEST_OK"
echo "TEST_MOEX_SESSION_PAPER_OBSERVATION_V1_OK"
