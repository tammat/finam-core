#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# USDRUB_RUNTIME_BLOCK_CALLSITE_AUDIT_V1
# Read-only аудит фактических callsite для USDRUBF runtime route.
# Ничего не меняет.


TARGET_FILE = Path("src/finam_core/pipelines/paper_pipeline.py")

PATTERNS = [
    "USDRUBF_PAPER_ACCUMULATION_BYPASS",
    "USD_PAPER_GOVERNANCE_BLOCKED",
    "PIPE_RISK_CTX",
    "PIPE_SMART_ENTRY",
    "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_ADVISORY_CONTINUE",
    "PIPE_TREND_ADVISORY_CONTINUE",
    "PIPE_SESSION_SIDE_GATE_DECISION",
    "PIPE_EDGE_GATE_STRICT_MODE",
    "_usd_paper_pilot_allows_intent_v1",
    "_usd_paper_pilot_profile_v1",
    "USDRUBF@RTSX",
    "PIPE_RUNTIME_STRATEGY_BLOCKED_V1",
]


def main() -> int:
    print("=== USDRUB RUNTIME BLOCK CALLSITE AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"target_file={TARGET_FILE}")

    text = TARGET_FILE.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    hits = []
    for i, line in enumerate(lines, start=1):
        for pattern in PATTERNS:
            if pattern in line:
                hits.append((i, pattern, line.strip()))

    print()
    print("USDRUB_CALLSITE_HITS")
    for i, pattern, line in hits:
        print(
            "USDRUB_CALLSITE_HIT "
            f"line={i} "
            f"pattern={pattern} "
            f"text={line[:240]}"
        )

    print()
    print("USDRUB_CALLSITE_CONTEXT")
    for i, pattern, line in hits:
        if pattern in {
            "USDRUBF_PAPER_ACCUMULATION_BYPASS",
            "USD_PAPER_GOVERNANCE_BLOCKED",
            "_usd_paper_pilot_allows_intent_v1",
            "PIPE_RUNTIME_STRATEGY_BLOCKED_V1",
        }:
            start = max(1, i - 20)
            end = min(len(lines), i + 25)
            print(f"USDRUB_CALLSITE_CONTEXT_BEGIN pattern={pattern} line={i}")
            for no in range(start, end + 1):
                print(f"{no}: {lines[no - 1]}")
            print(f"USDRUB_CALLSITE_CONTEXT_END pattern={pattern} line={i}")

    helper_present = int("def _is_runtime_strategy_blocked_v1" in text)
    generic_guard_present = int("PIPE_RUNTIME_STRATEGY_BLOCKED_V1" in text)
    bypass_present = int("USDRUBF_PAPER_ACCUMULATION_BYPASS" in text)
    usd_gate_present = int("_usd_paper_pilot_allows_intent_v1" in text)

    print()
    print("USDRUB_CALLSITE_AUDIT_SUMMARY")
    print(f"hits={len(hits)}")
    print(f"helper_present={helper_present}")
    print(f"generic_guard_present={generic_guard_present}")
    print(f"bypass_present={bypass_present}")
    print(f"usd_gate_present={usd_gate_present}")
    print("db_update=0")
    print("execution_changes_required=0")
    print("runtime_changes_required=1")

    if helper_present and generic_guard_present and bypass_present:
        print("VERDICT=USDRUB_BLOCK_GUARD_EXISTS_BUT_BYPASS_ROUTE_STILL_REQUIRES_PATCH")
    elif bypass_present:
        print("VERDICT=USDRUB_BYPASS_ROUTE_REQUIRES_PATCH")
    else:
        print("VERDICT=USDRUB_CALLSITE_REVIEW_REQUIRED")

    print("USDRUB_RUNTIME_BLOCK_CALLSITE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
