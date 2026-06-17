#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FUTURES REAL BLOCK GUARD DISPATCHER WIRING V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/finam_core/risk/futures_real_block_guard_v1.py \
  src/finam_core/execution/execution_dispatcher.py

grep -q "FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1" src/finam_core/execution/execution_dispatcher.py
grep -q "FUTURES_REAL_BLOCK_GUARD_DISPATCHER_BLOCKED" src/finam_core/execution/execution_dispatcher.py
grep -q "evaluate_futures_real_block_v1" src/finam_core/execution/execution_dispatcher.py
grep -q "orders_client.place_limit_order" src/finam_core/execution/execution_dispatcher.py

python3 - <<'PY'
from pathlib import Path

text = Path("src/finam_core/execution/execution_dispatcher.py").read_text()

guard_pos = text.find("FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1")
send_pos = text.find("result = self.orders_client.place_limit_order(")

print(f"guard_pos={guard_pos}")
print(f"send_pos={send_pos}")

if guard_pos == -1:
    raise SystemExit("FAIL: guard marker not found")

if send_pos == -1:
    raise SystemExit("FAIL: direct send call not found")

if guard_pos > send_pos:
    raise SystemExit("FAIL: guard is after send call")

print("DISPATCHER_GUARD_BEFORE_SEND_OK")
PY

PYTHONPATH=src python3 - <<'PY'
from datetime import date

from finam_core.risk.futures_real_block_guard_v1 import evaluate_futures_real_block_v1


cases = [
    ("BRN6@RTSX", "real", False),
    ("NGQ6@RTSX", "real", False),
    ("GDU6@RTSX", "real", False),
    ("USDRUBF@RTSX", "real", False),
    ("SBER@MISX", "real", True),
    ("BRN6@RTSX", "paper", True),
]

for symbol, mode, expected_allowed in cases:
    decision = evaluate_futures_real_block_v1(
        symbol=symbol,
        execution_mode=mode,
        current_date=date(2026, 6, 17),
    )

    print(
        "GUARD_CASE "
        f"symbol={symbol} "
        f"mode={mode} "
        f"allowed={int(decision.allowed)} "
        f"reason={decision.reason}"
    )

    if decision.allowed != expected_allowed:
        raise SystemExit(f"FAIL: unexpected guard decision for {symbol} {mode}")

print("FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1_OK")
PY

echo TEST_FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1_OK
