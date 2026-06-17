#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from finam_core.risk.futures_real_block_guard_v1 import evaluate_futures_real_block_v1


ROOT = Path(__file__).resolve().parents[3]

REQUIRED_MARKERS = {
    "src/finam_core/risk/futures_real_block_guard_v1.py": [
        "FUTURES_REAL_ALLOWED_AFTER",
        "FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01",
        "evaluate_futures_real_block_v1",
    ],
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
    "src/finam_core/adapters/grpc/orders_client.py": [
        "LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1",
        "LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_BLOCKED",
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
    "src/scripts/research/build_low_level_order_client_last_line_guard_review_v1.py": [
        "LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_COMPLETE",
        "LOW_LEVEL_ALREADY_GUARDED",
        "LEGACY_REAL_EXECUTION_DEPRECATE_OR_GUARD",
        "LEGACY_INFRA_USAGE_REVIEW",
    ],
    "src/scripts/research/build_futures_real_block_guard_final_healthcheck_v1.py": [
        "FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_OK",
        "FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_V1_OK",
    ],
}


POSITION_CHECKS = {
    "src/finam_core/execution/finam_order_client_adapter.py": [
        ("FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1", "self.client.place_limit_order"),
        ("FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1", "self.client.place_market_order"),
    ],
    "src/finam_core/execution/execution_dispatcher.py": [
        ("FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1", "self.orders_client.place_limit_order"),
    ],
    "src/finam_core/execution/oco_order_manager.py": [
        ("FUTURES_REAL_BLOCK_GUARD_OCO_WIRING_V1", "self.orders_client.place_limit_order"),
    ],
    "src/scripts/run_synthetic_protective_real_sell_adapter.py": [
        ("FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_WIRING_V1", "client.place_limit_order"),
        ("FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_WIRING_V1", "client.place_market_order"),
    ],
    "src/finam_core/adapters/grpc/orders_client.py": [
        ("LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1", "order = self._build_limit_order"),
        ("LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1", "token_reason = self._ensure_token()"),
    ],
}


def read_text(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def check_markers() -> list[str]:
    missing: list[str] = []

    for rel, markers in REQUIRED_MARKERS.items():
        text = read_text(rel)
        if not text:
            missing.append(f"{rel}:FILE_MISSING")
            continue

        for marker in markers:
            if marker not in text:
                missing.append(f"{rel}:{marker}")

    return missing


def check_positions() -> list[str]:
    failures: list[str] = []

    for rel, checks in POSITION_CHECKS.items():
        text = read_text(rel)
        if not text:
            failures.append(f"{rel}:FILE_MISSING")
            continue

        for guard_marker, send_marker in checks:
            guard_pos = text.find(guard_marker)
            send_pos = text.find(send_marker)

            print(
                "FULL_STACK_POSITION_CHECK "
                f"path={rel} "
                f"guard_marker={guard_marker} "
                f"send_marker={send_marker} "
                f"guard_pos={guard_pos} "
                f"send_pos={send_pos}"
            )

            if guard_pos == -1:
                failures.append(f"{rel}:{guard_marker}:MISSING")
                continue

            if send_pos == -1:
                failures.append(f"{rel}:{send_marker}:MISSING")
                continue

            if guard_pos > send_pos:
                failures.append(f"{rel}:{guard_marker}:AFTER:{send_marker}")

    return failures


def check_guard_decisions() -> list[str]:
    failures: list[str] = []

    cases = [
        ("BRN6@RTSX", "real", False),
        ("NGQ6@RTSX", "real", False),
        ("GDU6@RTSX", "real", False),
        ("USDRUBF@RTSX", "real", False),
        ("SBER@MISX", "real", True),
        ("BRN6@RTSX", "paper", True),
        ("BRN6@RTSX", "shadow", True),
        ("BRN6@RTSX", "production", False),
        ("BRN6@RTSX", "live", False),
    ]

    for symbol, mode, expected_allowed in cases:
        decision = evaluate_futures_real_block_v1(
            symbol=symbol,
            execution_mode=mode,
            current_date=date(2026, 6, 17),
        )

        print(
            "FULL_STACK_GUARD_CASE "
            f"symbol={symbol} "
            f"mode={mode} "
            f"allowed={int(decision.allowed)} "
            f"expected_allowed={int(expected_allowed)} "
            f"reason={decision.reason}"
        )

        if decision.allowed != expected_allowed:
            failures.append(
                f"{symbol}:{mode}:expected_{int(expected_allowed)}:got_{int(decision.allowed)}"
            )

    after_allowed = evaluate_futures_real_block_v1(
        symbol="BRN6@RTSX",
        execution_mode="real",
        current_date=date(2026, 7, 1),
    )

    print(
        "FULL_STACK_GUARD_CASE "
        f"symbol=BRN6@RTSX "
        f"mode=real "
        f"date=2026-07-01 "
        f"allowed={int(after_allowed.allowed)} "
        f"expected_allowed=1 "
        f"reason={after_allowed.reason}"
    )

    if not after_allowed.allowed:
        failures.append("BRN6@RTSX:real:2026-07-01:expected_1:got_0")

    return failures


def check_safety_env() -> list[str]:
    failures: list[str] = []

    expected_zero = [
        "RUNTIME_ALLOW",
        "EXECUTION_ENABLED",
        "REAL_TRADING_ENABLED",
    ]

    for key in expected_zero:
        value = os.getenv(key, "0")
        print(f"FULL_STACK_ENV {key}={value}")

        if value != "0":
            failures.append(f"{key}_NOT_ZERO")

    return failures


def main() -> int:
    print("=== FUTURES REAL BLOCK GUARD FULL STACK HEALTHCHECK V1 ===")
    print("mode=diagnostic")

    marker_missing = check_markers()
    position_failures = check_positions()
    guard_failures = check_guard_decisions()
    safety_failures = check_safety_env()

    print()
    print("FULL_STACK_HEALTHCHECK_SUMMARY")
    print(f"marker_missing={len(marker_missing)}")
    print(f"position_failures={len(position_failures)}")
    print(f"guard_failures={len(guard_failures)}")
    print(f"safety_failures={len(safety_failures)}")

    if marker_missing:
        print("MARKER_MISSING=" + ",".join(marker_missing))
    else:
        print("MARKER_MISSING=none")

    if position_failures:
        print("POSITION_FAILURES=" + ",".join(position_failures))
    else:
        print("POSITION_FAILURES=none")

    if guard_failures:
        print("GUARD_FAILURES=" + ",".join(guard_failures))
    else:
        print("GUARD_FAILURES=none")

    if safety_failures:
        print("SAFETY_FAILURES=" + ",".join(safety_failures))
    else:
        print("SAFETY_FAILURES=none")

    if marker_missing or position_failures or guard_failures or safety_failures:
        print("VERDICT=FUTURES_REAL_BLOCK_GUARD_FULL_STACK_HEALTHCHECK_FAILED")
        return 1

    print("VERDICT=FUTURES_REAL_BLOCK_GUARD_FULL_STACK_HEALTHCHECK_OK")
    print("FUTURES_REAL_BLOCK_GUARD_FULL_STACK_HEALTHCHECK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
