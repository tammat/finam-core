#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_RUNTIME_STATE_RU_V1_START"

"$PY_BIN" -m py_compile src/scripts/observability/build_ng_runtime_state_ru_v1.py

SYMBOL=NGN6@RTSX "$PY_BIN" src/scripts/observability/build_ng_runtime_state_ru_v1.py > /tmp/ng_runtime_state_ru_v1.out

grep -q "NG RUNTIME STATE RU V1" /tmp/ng_runtime_state_ru_v1.out
grep -q "ПОСЛЕДНИЕ FILLS" /tmp/ng_runtime_state_ru_v1.out
grep -q "POSITION_PROJECTION" /tmp/ng_runtime_state_ru_v1.out

echo "TEST_NG_RUNTIME_STATE_RU_V1_OK"
