#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


# Русский комментарий:
# EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_V1
# Read-only план исправления pre-signal guard для equity.
# Ищет в коде места, где используется br_volatility_too_low,
# high_vol_static_cap, compression_watch_active и equity strategy names.
# Ничего не меняет.


ROOT = Path(os.getenv("FINAM_CORE_ROOT", ".")).resolve()

SEARCH_TERMS = [
    "br_volatility_too_low",
    "compression_watch_active",
    "high_vol_static_cap",
    "low_vol_adaptive",
    "runtime_guard_pre_signal_block_audit_v1",
    "VOLATILITY_BREAKOUT_EQUITY",
    "MEAN_REVERSION_EQUITY",
]

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
}


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if should_skip(path):
            continue
        yield path


def main() -> int:
    print("=== EQUITY PRE SIGNAL GUARD PATCH PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"root={ROOT}")
    print()

    hits: list[tuple[str, int, str, str]] = []

    for path in iter_py_files(ROOT):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, start=1):
            for term in SEARCH_TERMS:
                if term in line:
                    hits.append((str(path.relative_to(ROOT)), i, term, line.strip()))

    print("EQUITY_PRE_SIGNAL_GUARD_CODE_HITS")
    for rel, line_no, term, line in hits:
        print(
            "EQUITY_PRE_SIGNAL_GUARD_CODE_HIT "
            f"file={rel} "
            f"line={line_no} "
            f"term={term} "
            f"code={line}"
        )

    files = sorted({h[0] for h in hits})
    br_reason_hits = [h for h in hits if h[2] == "br_volatility_too_low"]
    equity_hits = [h for h in hits if h[2] in {"VOLATILITY_BREAKOUT_EQUITY", "MEAN_REVERSION_EQUITY"}]
    guard_table_hits = [h for h in hits if h[2] == "runtime_guard_pre_signal_block_audit_v1"]

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_ROWS")

    if br_reason_hits:
        print(
            "EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_ROW "
            "issue=br_named_reason_used "
            "action=inspect_callsite_and_split_equity_reason "
            "recommended_fix=rename_or_route_to_equity_volatility_too_low "
            "risk=LOW_IF_RENAME_ONLY_HIGH_IF_GUARD_LOGIC_SHARED"
        )

    if equity_hits:
        print(
            "EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_ROW "
            "issue=equity_strategy_detected "
            "action=verify_strategy_resolution_and_guard_mapping "
            "recommended_fix=ensure_VOLATILITY_BREAKOUT_EQUITY_uses_equity_thresholds "
            "risk=MEDIUM"
        )

    if guard_table_hits:
        print(
            "EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_ROW "
            "issue=guard_audit_writer_detected "
            "action=inspect_writer_payload_for_threshold_atr_pct_volatility "
            "recommended_fix=store_guard_inputs_in_payload "
            "risk=LOW"
        )

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_SUMMARY")
    print(f"files_with_hits={len(files)}")
    print(f"hits_total={len(hits)}")
    print(f"br_volatility_reason_hits={len(br_reason_hits)}")
    print(f"equity_strategy_hits={len(equity_hits)}")
    print(f"guard_table_hits={len(guard_table_hits)}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if br_reason_hits and equity_hits:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_REQUIRED")
    elif br_reason_hits:
        print("VERDICT=BR_NAMED_REASON_RENAME_REVIEW_REQUIRED")
    else:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_CODE_PATH_NOT_FOUND")

    print("EQUITY_PRE_SIGNAL_GUARD_PATCH_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
