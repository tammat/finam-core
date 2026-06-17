#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

TARGETS = [
    "src/finam_core/execution/execution_dispatcher.py",
    "src/finam_core/execution/oco_order_manager.py",
    "src/finam_core/execution/real_execution.py",
    "src/scripts/run_synthetic_protective_real_sell_adapter.py",
    "src/scripts/run_protective_stop_real_execution_adapter.py",
    "src/scripts/run_real_buy_execution_adapter.py",
    "src/scripts/run_real_sell_execution_adapter.py",
    "src/finam_core/adapters/grpc/orders_client.py",
    "src/finam_core/infra/finam/client.py",
    "src/finam_core/infra/finam/adapter.py",
    "src/finam_core/infra/brokers/finam_rest.py",
]

SEND_PATTERNS = [
    "place_order(",
    "place_limit_order(",
    "place_market_order(",
    "orders_client.place_limit_order",
    "orders_client.place_market_order",
    "client.place_limit_order",
    "client.place_market_order",
    "client.place_order",
    "_post(",
]

SAFE_ADAPTER_MARKERS = [
    "FinamOrderClientAdapter",
    "futures_real_block_guard_v1",
    "evaluate_futures_real_block_v1",
    "FUTURES_REAL_BLOCK_GUARD",
]

REAL_MARKERS = [
    "REAL_BUY",
    "REAL_SELL",
    "protective_stop_real",
    "synthetic_protective_real_sell",
    "REAL_SELL_STOP_ENABLED",
    "SYNTHETIC_PROTECTIVE_SELL_ENABLED",
    "REAL_BUY_EXECUTION_ENABLED",
    "REAL_SELL_EXECUTION_ENABLED",
]


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def classify_file(rel: str, text: str, hits: list[tuple[int, str]]) -> tuple[str, str]:
    lower = text.lower()

    has_send = bool(hits)
    has_guard = any(marker.lower() in lower for marker in SAFE_ADAPTER_MARKERS)
    has_real_marker = any(marker.lower() in lower for marker in REAL_MARKERS)

    if not has_send:
        return "NO_SEND_CALL", "no direct send call"

    if has_guard:
        return "GUARDED_OR_ADAPTER_AWARE", "guard or FinamOrderClientAdapter marker present"

    if "run_synthetic_protective_real_sell_adapter.py" in rel:
        return "PROTECTIVE_DIRECT_SEND_REQUIRES_GUARD", "synthetic protective direct client send"

    if "run_protective_stop_real_execution_adapter.py" in rel:
        return "PROTECTIVE_REVIEW_REQUIRED", "protective stop script requires send-path review"

    if "execution_dispatcher.py" in rel:
        return "DISPATCHER_DIRECT_SEND_REQUIRES_GUARD", "dispatcher calls orders_client directly"

    if "oco_order_manager.py" in rel:
        return "OCO_DIRECT_SEND_REQUIRES_GUARD", "OCO manager calls orders_client directly"

    if "real_execution.py" in rel:
        return "LEGACY_REAL_EXECUTION_REQUIRES_GUARD_OR_DEPRECATION", "legacy real execution calls orders_client directly"

    if "orders_client.py" in rel:
        return "LOW_LEVEL_GRPC_CLIENT_REQUIRES_BASE_GUARD_REVIEW", "low-level order client"

    if "infra/finam/client.py" in rel or "infra/finam/adapter.py" in rel or "finam_rest.py" in rel:
        return "LEGACY_INFRA_CLIENT_REQUIRES_USAGE_REVIEW", "legacy infra send path"

    if has_real_marker:
        return "REAL_SEND_REVIEW_REQUIRED", "real marker and send call found"

    return "SEND_REVIEW_REQUIRED", "send call found"


def extract_hits(lines: list[str]) -> list[tuple[int, str]]:
    hits = []
    for i, line in enumerate(lines, start=1):
        lower = line.lower()
        if any(pattern.lower() in lower for pattern in SEND_PATTERNS):
            hits.append((i, line.rstrip()))
    return hits


def main() -> int:
    print("=== FUTURES REAL BLOCK GUARD PROTECTIVE WIRING AUDIT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    blockers = []
    review_rows = 0

    for rel in TARGETS:
        path = ROOT / rel
        if not path.exists():
            print(f"TARGET_MISSING path={rel}")
            continue

        lines = read_lines(path)
        text = "\n".join(lines)
        hits = extract_hits(lines)
        classification, reason = classify_file(rel, text, hits)

        print()
        print(
            "PROTECTIVE_WIRING_ROW "
            f"path={rel} "
            f"classification={classification} "
            f"hits={len(hits)} "
            f"reason={reason}"
        )

        for line_no, line in hits[:80]:
            print(
                "PROTECTIVE_WIRING_HIT "
                f"path={rel} "
                f"line={line_no} "
                f"text={line}"
            )

        if classification.endswith("REQUIRES_GUARD") or classification in {
            "OCO_DIRECT_SEND_REQUIRES_GUARD",
            "DISPATCHER_DIRECT_SEND_REQUIRES_GUARD",
            "PROTECTIVE_DIRECT_SEND_REQUIRES_GUARD",
        }:
            blockers.append(f"{rel}:{classification}")

        if classification != "NO_SEND_CALL":
            review_rows += 1

    print()
    print("PROTECTIVE_WIRING_SUMMARY")
    print(f"review_rows={review_rows}")
    print(f"guard_required_rows={len(blockers)}")

    if blockers:
        print("GUARD_REQUIRED=" + ",".join(blockers))
        print("VERDICT=PROTECTIVE_SEND_PATHS_REQUIRE_GUARD_WIRING")
    else:
        print("GUARD_REQUIRED=none")
        print("VERDICT=PROTECTIVE_SEND_PATHS_ALREADY_GUARDED_OR_LOW_RISK")

    print("FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
