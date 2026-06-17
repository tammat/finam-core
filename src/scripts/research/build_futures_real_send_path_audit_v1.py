#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

TARGET_FILES = [
    "src/finam_core/execution/finam_order_client_adapter.py",
    "src/finam_core/execution/finam_execution_engine.py",
    "src/finam_core/execution/real_buy_execution_adapter.py",
    "src/finam_core/execution/real_sell_execution_adapter.py",
    "src/finam_core/execution/oms_dispatch_guard.py",
    "src/finam_core/execution/order_manager.py",
    "src/scripts/run_real_buy_execution_adapter.py",
    "src/scripts/run_real_sell_execution_adapter.py",
    "src/scripts/run_protective_stop_real_execution_adapter.py",
    "src/scripts/run_synthetic_protective_real_sell_adapter.py",
]

PATTERNS = [
    "place_order",
    "send_order",
    "create_order",
    "new_order",
    "submit_order",
    "REAL_BUY",
    "REAL_SELL",
    "execution_enabled",
    "REAL_TRADING_ENABLED",
    "ENABLE_REAL_EXECUTION",
    "dry_run",
    "DRY_RUN",
]


def extract_hits(path: Path) -> list[tuple[int, str]]:
    if not path.exists():
        return []

    hits: list[tuple[int, str]] = []
    lines = path.read_text(errors="ignore").splitlines()

    for i, line in enumerate(lines, start=1):
        lower = line.lower()
        if any(p.lower() in lower for p in PATTERNS):
            hits.append((i, line.rstrip()))

    return hits


def classify_file(rel: str, hits: list[tuple[int, str]]) -> str:
    text = "\n".join(line for _, line in hits).lower()

    if "finam_order_client_adapter.py" in rel:
        return "PRIMARY_BROKER_SEND_ADAPTER"

    if "finam_execution_engine.py" in rel:
        return "EXECUTION_ENGINE_SEND_LAYER"

    if "real_buy_execution_adapter.py" in rel or "real_sell_execution_adapter.py" in rel:
        return "REAL_SIDE_ADAPTER"

    if "protective" in rel or "synthetic_protective" in rel:
        return "PROTECTIVE_REAL_SEND_PATH"

    if "oms_dispatch_guard.py" in rel:
        return "OMS_DISPATCH_GUARD"

    if "order_manager.py" in rel:
        return "ORDER_MANAGER_REVIEW"

    if "place_order" in text or "send_order" in text or "create_order" in text or "new_order" in text:
        return "REAL_SEND_CANDIDATE"

    return "LOW_PRIORITY_REVIEW"


def main() -> int:
    print("=== FUTURES REAL SEND PATH AUDIT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    missing = []
    primary_candidates = []

    for rel in TARGET_FILES:
        path = ROOT / rel
        hits = extract_hits(path)

        if not path.exists():
            missing.append(rel)
            print(f"SEND_PATH_FILE_MISSING path={rel}")
            continue

        classification = classify_file(rel, hits)

        print()
        print(
            "SEND_PATH_FILE "
            f"path={rel} "
            f"classification={classification} "
            f"hits={len(hits)}"
        )

        for line_no, line in hits[:80]:
            print(
                "SEND_PATH_HIT "
                f"path={rel} "
                f"line={line_no} "
                f"text={line}"
            )

        if classification in {
            "PRIMARY_BROKER_SEND_ADAPTER",
            "EXECUTION_ENGINE_SEND_LAYER",
            "REAL_SIDE_ADAPTER",
            "PROTECTIVE_REAL_SEND_PATH",
        }:
            primary_candidates.append(rel)

    print()
    print("SEND_PATH_AUDIT_SUMMARY")
    print(f"missing_files={len(missing)}")
    print(f"primary_candidates={len(primary_candidates)}")

    for p in primary_candidates:
        print(f"PRIMARY_CANDIDATE path={p}")

    if "src/finam_core/execution/finam_order_client_adapter.py" in primary_candidates:
        verdict = "PRIMARY_BROKER_ADAPTER_FOUND"
    elif primary_candidates:
        verdict = "PRIMARY_SEND_LAYER_REVIEW_REQUIRED"
    else:
        verdict = "NO_PRIMARY_SEND_PATH_FOUND"

    print(f"VERDICT={verdict}")

    if verdict == "NO_PRIMARY_SEND_PATH_FOUND":
        raise SystemExit(1)

    print("FUTURES_REAL_SEND_PATH_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
