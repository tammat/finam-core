#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MOEX_SESSION_OBSERVATION_SOFT_READINESS_V1 ==="

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
grep -q "orders_create=0" "$out"
grep -q "execution_intents_create=0" "$out"

if grep -q "step=src/scripts/research/build_real_trading_readiness_gates_v1.py" "$out"; then
  grep -q "effective_ok=True code=1 step=src/scripts/research/build_real_trading_readiness_gates_v1.py" "$out"
fi

if grep -q "step=src/scripts/research/build_monday_paper_startup_readiness_v1.py" "$out"; then
  grep -q "effective_ok=True code=1 step=src/scripts/research/build_monday_paper_startup_readiness_v1.py" "$out"
fi

grep -q "VERDICT=MOEX_SESSION_PAPER_OBSERVATION_OK" "$out"

echo "VERDICT=MOEX_SESSION_OBSERVATION_SOFT_READINESS_TEST_OK"
echo "TEST_MOEX_SESSION_OBSERVATION_SOFT_READINESS_V1_OK"
