#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

TARGETS = [
    "src/finam_core/execution/real_execution.py",
    "src/finam_core/adapters/grpc/orders_client.py",
    "src/finam_core/infra/finam/client.py",
    "src/finam_core/infra/finam/adapter.py",
    "src/finam_core/infra/brokers/finam_rest.py",
]

PRIMARY_GUARDED_PATHS = [
    "src/finam_core/execution/finam_order_client_adapter.py",
    "src/finam_core/execution/execution_dispatcher.py",
    "src/finam_core/execution/oco_order_manager.py",
    "src/scripts/run_synthetic_protective_real_sell_adapter.py",
]

PRIMARY_GUARD_MARKERS = {
    "src/finam_core/execution/finam_order_client_adapter.py": "FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1",
    "src/finam_core/execution/execution_dispatcher.py": "FUTURES_REAL_BLOCK_GUARD_DISPATCHER_WIRING_V1",
    "src/finam_core/execution/oco_order_manager.py": "FUTURES_REAL_BLOCK_GUARD_OCO_WIRING_V1",
    "src/scripts/run_synthetic_protective_real_sell_adapter.py": "FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_WIRING_V1",
}

SEND_PATTERNS = [
    "place_order(",
    "place_limit_order(",
    "place_market_order(",
    "orders_client.place_limit_order",
    "orders_client.place_market_order",
    "client.place_order",
    "client.place_limit_order",
    "client.place_market_order",
    "return self._post(self.cfg.routes.place_order",
]

GUARD_MARKERS = [
    "evaluate_futures_real_block_v1",
    "FUTURES_REAL_BLOCK_GUARD",
]


def read_text(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def extract_hits(text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        lower = line.lower()
        if any(pattern.lower() in lower for pattern in SEND_PATTERNS):
            hits.append((line_no, line.rstrip()))
    return hits


def has_any_marker(text: str, markers: list[str]) -> bool:
    lower = text.lower()
    return any(marker.lower() in lower for marker in markers)


def primary_guard_complete() -> tuple[bool, list[str]]:
    missing: list[str] = []

    for rel, marker in PRIMARY_GUARD_MARKERS.items():
        text = read_text(rel)
        if not text:
            missing.append(f"{rel}:FILE_MISSING")
            continue

        if marker not in text:
            missing.append(f"{rel}:{marker}")

    return len(missing) == 0, missing


def classify(rel: str, text: str, hits: list[tuple[int, str]]) -> tuple[str, str, str]:
    if not text:
        return "MISSING", "file missing", "restore or remove from review"

    if not hits:
        return "NO_DIRECT_SEND", "no direct send call", "no action"

    if has_any_marker(text, GUARD_MARKERS):
        return "LOW_LEVEL_ALREADY_GUARDED", "guard marker present", "keep under regression test"

    if rel == "src/finam_core/adapters/grpc/orders_client.py":
        return (
            "LOW_LEVEL_GRPC_LAST_LINE_GUARD_CANDIDATE",
            "primary low-level gRPC order client has direct send methods",
            "candidate for last-line futures guard",
        )

    if rel == "src/finam_core/execution/real_execution.py":
        return (
            "LEGACY_REAL_EXECUTION_DEPRECATE_OR_GUARD",
            "legacy real execution directly calls orders_client",
            "deprecate if unused; otherwise add guard before use",
        )

    if rel.startswith("src/finam_core/infra/finam/") or rel == "src/finam_core/infra/brokers/finam_rest.py":
        return (
            "LEGACY_INFRA_USAGE_REVIEW",
            "legacy infra send path exists outside current guarded route",
            "keep disabled; guard only if usage is proven",
        )

    return "SEND_REVIEW_REQUIRED", "direct send found", "manual review"


def main() -> int:
    print("=== LOW LEVEL ORDER CLIENT LAST LINE GUARD REVIEW V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    primary_ok, primary_missing = primary_guard_complete()

    print()
    print("PRIMARY_GUARD_STATUS")
    print(f"primary_guard_complete={int(primary_ok)}")
    if primary_missing:
        print("PRIMARY_GUARD_MISSING=" + ",".join(primary_missing))
    else:
        print("PRIMARY_GUARD_MISSING=none")

    low_level_candidates: list[str] = []
    legacy_review: list[str] = []
    missing_files: list[str] = []
    direct_send_rows = 0

    for rel in TARGETS:
        text = read_text(rel)
        hits = extract_hits(text)
        classification, reason, action = classify(rel, text, hits)

        if hits:
            direct_send_rows += 1

        if classification == "LOW_LEVEL_GRPC_LAST_LINE_GUARD_CANDIDATE":
            low_level_candidates.append(rel)

        if classification in {
            "LEGACY_REAL_EXECUTION_DEPRECATE_OR_GUARD",
            "LEGACY_INFRA_USAGE_REVIEW",
            "SEND_REVIEW_REQUIRED",
        }:
            legacy_review.append(rel)

        if classification == "MISSING":
            missing_files.append(rel)

        print()
        print(
            "LOW_LEVEL_REVIEW_ROW "
            f"path={rel} "
            f"classification={classification} "
            f"hits={len(hits)} "
            f"has_guard={int(has_any_marker(text, GUARD_MARKERS))} "
            f"reason={reason} "
            f"recommended_action={action}"
        )

        for line_no, line in hits[:80]:
            print(
                "LOW_LEVEL_REVIEW_HIT "
                f"path={rel} "
                f"line={line_no} "
                f"text={line}"
            )

    print()
    print("LOW_LEVEL_REVIEW_SUMMARY")
    print(f"direct_send_rows={direct_send_rows}")
    print(f"low_level_guard_candidates={len(low_level_candidates)}")
    print(f"legacy_review_rows={len(legacy_review)}")
    print(f"missing_files={len(missing_files)}")

    if low_level_candidates:
        print("LOW_LEVEL_GUARD_CANDIDATES=" + ",".join(low_level_candidates))
    else:
        print("LOW_LEVEL_GUARD_CANDIDATES=none")

    if legacy_review:
        print("LEGACY_REVIEW=" + ",".join(legacy_review))
    else:
        print("LEGACY_REVIEW=none")

    if missing_files:
        print("MISSING_FILES=" + ",".join(missing_files))
    else:
        print("MISSING_FILES=none")

    if not primary_ok:
        print("VERDICT=LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_BLOCKED_PRIMARY_GUARD_INCOMPLETE")
        return 1

    if missing_files:
        print("VERDICT=LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_BLOCKED_MISSING_FILES")
        return 1

    print("VERDICT=LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_COMPLETE")
    print("LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
