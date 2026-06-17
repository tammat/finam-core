#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

TARGETS = [
    "src/finam_core/execution/finam_order_client_adapter.py",
    "src/finam_core/execution/execution_dispatcher.py",
    "src/finam_core/execution/oco_order_manager.py",
    "src/scripts/run_synthetic_protective_real_sell_adapter.py",
    "src/scripts/run_protective_stop_real_execution_adapter.py",
    "src/scripts/run_real_buy_execution_adapter.py",
    "src/scripts/run_real_sell_execution_adapter.py",
    "src/finam_core/execution/real_execution.py",
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

GUARD_MARKERS = [
    "FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1",
    "FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1",
    "FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_WIRING_V1",
    "FUTURES_REAL_BLOCK_GUARD_OCO_WIRING_V1",
    "evaluate_futures_real_block_v1",
]

EXPECTED_GUARDED = {
    "src/finam_core/execution/finam_order_client_adapter.py": "BROKER_ADAPTER_GUARDED",
    "src/finam_core/execution/execution_dispatcher.py": "DISPATCHER_GUARDED",
    "src/finam_core/execution/oco_order_manager.py": "OCO_GUARDED",
    "src/scripts/run_synthetic_protective_real_sell_adapter.py": "SYNTHETIC_PROTECTIVE_GUARDED",
}


def read_text(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def hits_for(text: str) -> list[tuple[int, str]]:
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        lower = line.lower()
        if any(p.lower() in lower for p in SEND_PATTERNS):
            hits.append((i, line.rstrip()))
    return hits


def has_guard(text: str) -> bool:
    lower = text.lower()
    return any(m.lower() in lower for m in GUARD_MARKERS)


def classify(rel: str, text: str, hits: list[tuple[int, str]]) -> tuple[str, str]:
    if not text:
        return "MISSING", "file missing"

    if not hits:
        return "NO_DIRECT_SEND", "no direct send call"

    if rel in EXPECTED_GUARDED:
        if has_guard(text):
            return EXPECTED_GUARDED[rel], "expected send path has futures guard"
        return "GUARD_REQUIRED", "expected guarded send path has no futures guard"

    if "real_execution.py" in rel:
        return "LEGACY_REAL_EXECUTION_REVIEW", "legacy real execution direct send remains review item"

    if "adapters/grpc/orders_client.py" in rel:
        return "LOW_LEVEL_GRPC_CLIENT_REVIEW", "low-level client remains last-line review item"

    if "infra/finam/client.py" in rel or "infra/finam/adapter.py" in rel or "finam_rest.py" in rel:
        return "LEGACY_INFRA_REVIEW", "legacy infra path remains usage review item"

    if has_guard(text):
        return "GUARDED_REVIEW", "guard marker present"

    return "SEND_REVIEW_REQUIRED", "send call exists but not expected guarded path"


def main() -> int:
    print("=== FUTURES REAL BLOCK GUARD PROTECTIVE WIRING AUDIT V2 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    guard_required = []
    review = []
    guarded = []

    for rel in TARGETS:
        text = read_text(rel)
        hits = hits_for(text)
        classification, reason = classify(rel, text, hits)

        print()
        print(
            "PROTECTIVE_WIRING_V2_ROW "
            f"path={rel} "
            f"classification={classification} "
            f"hits={len(hits)} "
            f"has_guard={int(has_guard(text))} "
            f"reason={reason}"
        )

        for line_no, line in hits[:60]:
            print(
                "PROTECTIVE_WIRING_V2_HIT "
                f"path={rel} "
                f"line={line_no} "
                f"text={line}"
            )

        if classification == "GUARD_REQUIRED":
            guard_required.append(rel)
        elif classification.endswith("_REVIEW") or classification == "SEND_REVIEW_REQUIRED":
            review.append(rel)
        elif "GUARDED" in classification:
            guarded.append(rel)

    print()
    print("PROTECTIVE_WIRING_V2_SUMMARY")
    print(f"guarded_rows={len(guarded)}")
    print(f"review_rows={len(review)}")
    print(f"guard_required_rows={len(guard_required)}")

    if guarded:
        print("GUARDED=" + ",".join(guarded))
    else:
        print("GUARDED=none")

    if review:
        print("REVIEW=" + ",".join(review))
    else:
        print("REVIEW=none")

    if guard_required:
        print("GUARD_REQUIRED=" + ",".join(guard_required))
        print("VERDICT=FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_INCOMPLETE")
        raise SystemExit(1)

    print("GUARD_REQUIRED=none")
    print("VERDICT=FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_COMPLETE")
    print("FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_AUDIT_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
