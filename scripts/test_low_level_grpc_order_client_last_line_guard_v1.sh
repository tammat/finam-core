#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST LOW LEVEL GRPC ORDER CLIENT LAST LINE GUARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/finam_core/risk/futures_real_block_guard_v1.py \
  src/finam_core/adapters/grpc/orders_client.py

grep -q "LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1" \
  src/finam_core/adapters/grpc/orders_client.py

grep -q "LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_BLOCKED" \
  src/finam_core/adapters/grpc/orders_client.py

grep -q "evaluate_futures_real_block_v1" \
  src/finam_core/adapters/grpc/orders_client.py

python3 - <<'PY'
from pathlib import Path

text = Path("src/finam_core/adapters/grpc/orders_client.py").read_text()

marker = "LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1"

first_guard_pos = text.find(marker)
second_guard_pos = text.rfind(marker)

limit_build_pos = text.find("order = self._build_limit_order(")
market_token_pos = text.find("token_reason = self._ensure_token()")

print(f"first_guard_pos={first_guard_pos}")
print(f"second_guard_pos={second_guard_pos}")
print(f"limit_build_pos={limit_build_pos}")
print(f"market_token_pos={market_token_pos}")

if first_guard_pos == -1:
    raise SystemExit("FAIL: first guard marker not found")

if second_guard_pos == -1 or second_guard_pos == first_guard_pos:
    raise SystemExit("FAIL: second guard marker not found")

if limit_build_pos == -1:
    raise SystemExit("FAIL: limit build point not found")

if market_token_pos == -1:
    raise SystemExit("FAIL: market token point not found")

if first_guard_pos > limit_build_pos:
    raise SystemExit("FAIL: limit guard is after limit build/send path")

if second_guard_pos > market_token_pos:
    raise SystemExit("FAIL: market guard is after token/send path")

print("LOW_LEVEL_GRPC_GUARD_BEFORE_SEND_OK")
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
    ("BRN6@RTSX", "shadow", True),
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

print("LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1_OK")
PY

echo TEST_LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1_OK
