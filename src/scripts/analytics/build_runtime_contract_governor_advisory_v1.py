#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess

ENTRY_BLOCK_DAYS = int(os.getenv("CONTRACT_SELECTOR_ENTRY_BLOCK_DAYS", "3"))
WATCH_DAYS = int(os.getenv("CONTRACT_SELECTOR_WATCH_DAYS", "7"))

CMD = [
    "python",
    "src/scripts/analytics/build_contract_selector_decision_table_v1.py",
]

def severity_for(decision: str, days_text: str) -> tuple[str, str]:
    try:
        days = int(days_text)
    except Exception:
        days = None

    if decision == "CALENDAR_MISSING":
        return "CRITICAL", "calendar_missing"

    if decision == "NO_RUNTIME_SYMBOL":
        return "CRITICAL", "runtime_symbol_missing"

    if days is not None and days <= ENTRY_BLOCK_DAYS:
        return "CRITICAL", "expiry_entry_block_window"

    if decision == "ROLLOVER_REQUIRED":
        return "CRITICAL", "rollover_required"

    if decision == "RUNTIME_AHEAD_BUT_LESS_LIQUID":
        return "WARNING", "runtime_ahead_less_liquid"

    if days is not None and days <= WATCH_DAYS:
        return "WARNING", "expiry_watch_window"

    if decision == "RUNTIME_MATCHES_SELECTOR":
        return "OK", "runtime_matches_selector"

    return "WARNING", "review_required"

def parse_fields(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in line.split():
        if "=" not in token:
            continue
        k, v = token.split("=", 1)
        out[k] = v
    return out

def main() -> None:
    print("=== RUNTIME CONTRACT GOVERNOR ADVISORY V1 ===")
    print("mode=advisory_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"entry_block_days={ENTRY_BLOCK_DAYS}")
    print(f"watch_days={WATCH_DAYS}")
    print()

    proc = subprocess.run(CMD, text=True, capture_output=True, check=False)

    if proc.returncode != 0:
        print("GOVERNOR_ROWS")
        print(
            "GOVERNOR_ROW "
            "root=UNKNOWN "
            "runtime_symbol=UNKNOWN "
            "decision=DECISION_TABLE_FAILED "
            "severity=CRITICAL "
            "action=REVIEW "
            "reason=decision_table_failed"
        )
        print()
        print("VERDICT=RUNTIME_CONTRACT_GOVERNOR_DECISION_TABLE_FAILED")
        print("RUNTIME_CONTRACT_GOVERNOR_ADVISORY_V1_OK")
        return

    rows = []
    for line in proc.stdout.splitlines():
        if not line.startswith("DECISION_ROW "):
            continue
        fields = parse_fields(line)
        rows.append(fields)

    print("GOVERNOR_ROWS")

    critical = 0
    warning = 0
    ok = 0

    for r in rows:
        decision = r.get("decision", "UNKNOWN")
        days_text = r.get("days_to_current_last_trade", "")
        severity, gov_reason = severity_for(decision, days_text)

        if severity == "CRITICAL":
            critical += 1
        elif severity == "WARNING":
            warning += 1
        else:
            ok += 1

        print(
            "GOVERNOR_ROW "
            f"root={r.get('root')} "
            f"runtime_symbol={r.get('runtime_symbol')} "
            f"calendar_current={r.get('calendar_current')} "
            f"calendar_next={r.get('calendar_next')} "
            f"selector_liquidity={r.get('selector_liquidity')} "
            f"days_to_current_last_trade={days_text} "
            f"decision={decision} "
            f"severity={severity} "
            f"action={r.get('action')} "
            f"reason={gov_reason} "
            f"decision_reason={r.get('reason')}"
        )

    print()
    print(f"ROWS={len(rows)}")
    print(f"OK_ROWS={ok}")
    print(f"WARNING_ROWS={warning}")
    print(f"CRITICAL_ROWS={critical}")

    if critical > 0:
        verdict = "CRITICAL_REVIEW_REQUIRED"
    elif warning > 0:
        verdict = "WARNING_REVIEW_REQUIRED"
    else:
        verdict = "RUNTIME_CONTRACTS_OK"

    print(f"VERDICT={verdict}")
    print("RUNTIME_CONTRACT_GOVERNOR_ADVISORY_V1_OK")

if __name__ == "__main__":
    main()
