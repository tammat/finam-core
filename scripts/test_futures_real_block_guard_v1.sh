#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FUTURES REAL BLOCK GUARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile src/finam_core/risk/futures_real_block_guard_v1.py

PYTHONPATH=src python3 - <<'PY'
from datetime import date

from finam_core.risk.futures_real_block_guard_v1 import (
    FuturesRealBlockGuardV1,
    evaluate_futures_real_block_v1,
)


guard = FuturesRealBlockGuardV1()

cases = [
    {
        "name": "block_br_real_before_date",
        "symbol": "BRN6@RTSX",
        "execution_mode": "real",
        "current_date": date(2026, 6, 17),
        "expected_allowed": False,
        "expected_reason": "FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01",
    },
    {
        "name": "block_ng_live_before_date",
        "symbol": "NGQ6@RTSX",
        "execution_mode": "live",
        "current_date": date(2026, 6, 17),
        "expected_allowed": False,
        "expected_reason": "FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01",
    },
    {
        "name": "allow_futures_paper_before_date",
        "symbol": "NGQ6@RTSX",
        "execution_mode": "paper",
        "current_date": date(2026, 6, 17),
        "expected_allowed": True,
        "expected_reason": "FUTURES_REAL_BLOCK_GUARD_PASS",
    },
    {
        "name": "allow_futures_real_after_date",
        "symbol": "BRN6@RTSX",
        "execution_mode": "real",
        "current_date": date(2026, 7, 1),
        "expected_allowed": True,
        "expected_reason": "FUTURES_REAL_BLOCK_GUARD_PASS",
    },
    {
        "name": "allow_equity_real_before_date",
        "symbol": "SBER@MISX",
        "execution_mode": "real",
        "current_date": date(2026, 6, 17),
        "expected_allowed": True,
        "expected_reason": "FUTURES_REAL_BLOCK_GUARD_PASS",
    },
    {
        "name": "explicit_futures_kind_blocks",
        "symbol": "CUSTOM@MISX",
        "instrument_kind": "futures",
        "execution_mode": "production",
        "current_date": date(2026, 6, 17),
        "expected_allowed": False,
        "expected_reason": "FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01",
    },
]

for case in cases:
    decision = guard.evaluate(
        symbol=case["symbol"],
        execution_mode=case["execution_mode"],
        current_date=case["current_date"],
        instrument_kind=case.get("instrument_kind"),
    )

    print(
        "CASE "
        f"name={case['name']} "
        f"symbol={decision.symbol} "
        f"mode={decision.execution_mode} "
        f"kind={decision.instrument_kind} "
        f"allowed={int(decision.allowed)} "
        f"reason={decision.reason} "
        f"current_date={decision.current_date} "
        f"allowed_after={decision.allowed_after}"
    )

    if decision.allowed != case["expected_allowed"]:
        raise SystemExit(f"FAIL_ALLOWED name={case['name']}")

    if decision.reason != case["expected_reason"]:
        raise SystemExit(f"FAIL_REASON name={case['name']} reason={decision.reason}")

wrapper_decision = evaluate_futures_real_block_v1(
    symbol="BRM6@RTSX",
    execution_mode="real",
    current_date=date(2026, 6, 17),
)

if wrapper_decision.allowed:
    raise SystemExit("FAIL_WRAPPER_SHOULD_BLOCK")

print("FUTURES_REAL_BLOCK_GUARD_V1_OK")
PY

echo TEST_FUTURES_REAL_BLOCK_GUARD_V1_OK
