#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from finam_core.risk.futures_real_block_guard_v1 import evaluate_futures_real_block_v1


ROOT = Path(__file__).resolve().parents[3]

REQUIRED_MARKERS = {
    "src/finam_core/execution/finam_order_client_adapter.py": [
        "FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1",
        "FUTURES_REAL_BLOCK_GUARD_BROKER_BLOCKED",
        "evaluate_futures_real_block_v1",
    ],
    "src/finam_core/execution/execution_dispatcher.py": [
        "FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1",
        "FUTURES_REAL_BLOCK_GUARD_DISPATCHER_BLOCKED",
        "evaluate_futures_real_block_v1",
    ],
    "src/finam_core/execution/oco_order_manager.py": [
        "FUTURES_REAL_BLOCK_GUARD_OCO_WIRING_V1",
        "FUTURES_REAL_BLOCK_GUARD_OCO_BLOCKED",
        "evaluate_futures_real_block_v1",
    ],
    "src/scripts/run_synthetic_protective_real_sell_adapter.py": [
        "FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_WIRING_V1",
        "FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_BLOCKED",
        "evaluate_futures_real_block_v1",
    ],
    "src/scripts/research/build_futures_real_block_guard_protective_wiring_audit_v2.py": [
        "FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_COMPLETE",
        "guard_required_rows",
        "BROKER_ADAPTER_GUARDED",
        "DISPATCHER_GUARDED",
        "OCO_GUARDED",
        "SYNTHETIC_PROTECTIVE_GUARDED",
    ],
}


def file_text(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def check_markers() -> tuple[int, list[str]]:
    missing = []
    checked = 0

    for rel, markers in REQUIRED_MARKERS.items():
        text = file_text(rel)
        if not text:
            missing.append(f"{rel}:FILE_MISSING")
            continue

        for marker in markers:
            checked += 1
            if marker not in text:
                missing.append(f"{rel}:{marker}")

    return checked, missing


def check_guard_decisions() -> tuple[int, list[str]]:
    cases = [
        ("BRN6@RTSX", "real", False),
        ("NGQ6@RTSX", "real", False),
        ("GDU6@RTSX", "real", False),
        ("USDRUBF@RTSX", "real", False),
        ("SBER@MISX", "real", True),
        ("BRN6@RTSX", "paper", True),
        ("BRN6@RTSX", "shadow", True),
    ]

    failures = []

    for symbol, mode, expected_allowed in cases:
        decision = evaluate_futures_real_block_v1(
            symbol=symbol,
            execution_mode=mode,
            current_date=date(2026, 6, 17),
        )

        print(
            "FINAL_HEALTHCHECK_GUARD_CASE "
            f"symbol={symbol} "
            f"mode={mode} "
            f"allowed={int(decision.allowed)} "
            f"expected_allowed={int(expected_allowed)} "
            f"reason={decision.reason}"
        )

        if decision.allowed != expected_allowed:
            failures.append(f"{symbol}:{mode}:expected_{expected_allowed}:got_{decision.allowed}")

    return len(cases), failures


def main() -> int:
    print("=== FUTURES REAL BLOCK GUARD FINAL HEALTHCHECK V1 ===")

    runtime_allow = os.getenv("RUNTIME_ALLOW", "0")
    execution_enabled = os.getenv("EXECUTION_ENABLED", "0")
    real_trading_enabled = os.getenv("REAL_TRADING_ENABLED", "0")

    print(f"runtime_allow={runtime_allow}")
    print(f"execution_enabled={execution_enabled}")
    print(f"real_trading_enabled={real_trading_enabled}")

    marker_checked, marker_missing = check_markers()
    guard_cases, guard_failures = check_guard_decisions()

    safety_failures = []

    if runtime_allow != "0":
        safety_failures.append("RUNTIME_ALLOW_NOT_ZERO")

    if execution_enabled != "0":
        safety_failures.append("EXECUTION_ENABLED_NOT_ZERO")

    if real_trading_enabled != "0":
        safety_failures.append("REAL_TRADING_ENABLED_NOT_ZERO")

    print()
    print("FINAL_HEALTHCHECK_SUMMARY")
    print(f"marker_checked={marker_checked}")
    print(f"marker_missing={len(marker_missing)}")
    print(f"guard_cases={guard_cases}")
    print(f"guard_failures={len(guard_failures)}")
    print(f"safety_failures={len(safety_failures)}")

    if marker_missing:
        print("MARKER_MISSING=" + ",".join(marker_missing))
    else:
        print("MARKER_MISSING=none")

    if guard_failures:
        print("GUARD_FAILURES=" + ",".join(guard_failures))
    else:
        print("GUARD_FAILURES=none")

    if safety_failures:
        print("SAFETY_FAILURES=" + ",".join(safety_failures))
    else:
        print("SAFETY_FAILURES=none")

    if marker_missing or guard_failures or safety_failures:
        print("VERDICT=FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_FAILED")
        return 1

    print("VERDICT=FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_OK")
    print("FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
