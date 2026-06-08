#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ROOTS = [x.strip().upper() for x in os.getenv("CONTRACT_SELECTOR_ROOTS", "BR,NG").split(",") if x.strip()]
ENTRY_BLOCK_DAYS = int(os.getenv("CONTRACT_SELECTOR_ENTRY_BLOCK_DAYS", "3"))
WATCH_DAYS = int(os.getenv("CONTRACT_SELECTOR_WATCH_DAYS", "7"))

DEFAULT_RUNTIME_SYMBOLS = os.getenv(
    "RUNTIME_ACTIVE_CONTRACT_SYMBOLS",
    "BRN6@RTSX,NGN6@RTSX",
)

SQL = """
SELECT
    root_symbol,
    symbol,
    contract_role,
    last_trade_date,
    expiration_date,
    (last_trade_date - CURRENT_DATE) AS days_to_last_trade
FROM futures_contract_calendar
WHERE root_symbol = ANY(%s)
  AND last_trade_date >= CURRENT_DATE
ORDER BY root_symbol, last_trade_date;
"""

def normalize_symbol(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    if "@" in value:
        return value
    return f"{value}@RTSX"

def root_for(symbol: str) -> str:
    symbol = symbol.upper()
    if symbol.startswith("BR"):
        return "BR"
    if symbol.startswith("NG"):
        return "NG"
    return "UNKNOWN"

def read_runtime_symbols() -> list[str]:
    try:
        proc = subprocess.run(
            [
                "systemctl",
                "show",
                "finam-paper-pipeline.service",
                "-p",
                "Environment",
                "--no-pager",
                "--value",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        env_text = proc.stdout or ""
    except Exception:
        env_text = ""

    candidates: list[str] = []

    patterns = [
        r"ACTIVE_BR_SYMBOLS=([^\s]+)",
        r"ACTIVE_NG_SYMBOLS=([^\s]+)",
        r"ROOT_ACTIVE_BR_SYMBOLS=([^\s]+)",
        r"ROOT_ACTIVE_NG_SYMBOLS=([^\s]+)",
        r"RUNTIME_ACTIVE_CONTRACT_SYMBOLS=([^\s]+)",
        r"SYMBOLS=([^\s]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, env_text)
        if match:
            candidates.extend(match.group(1).split(","))

    if not candidates:
        candidates = DEFAULT_RUNTIME_SYMBOLS.split(",")

    return sorted({normalize_symbol(x) for x in candidates if x.strip()})

def choose_calendar_contract(chain: list[dict]) -> tuple[str, str, int | None, str]:
    if not chain:
        return "NONE", "NO_CALENDAR", None, "calendar_missing"

    current = chain[0]
    next_contract = chain[1] if len(chain) > 1 else None

    current_symbol = current["symbol"]
    days = current["days_to_last_trade"]

    if days is not None and days <= ENTRY_BLOCK_DAYS:
        if next_contract:
            return next_contract["symbol"], "SELECT_NEXT_STOP_CURRENT_ENTRIES", days, "current_contract_expiring"
        return current_symbol, "STOP_NEW_ENTRIES", days, "current_contract_expiring_no_next"

    if days is not None and days <= WATCH_DAYS:
        if next_contract:
            return next_contract["symbol"], "SELECT_NEXT_ROLLOVER_WATCH", days, "current_contract_near_expiry"
        return current_symbol, "WATCH_CURRENT_NO_NEXT", days, "current_contract_near_expiry_no_next"

    return current_symbol, "SELECT_CURRENT", days, "current_contract_safe"

def classify_runtime(runtime_symbol: str, selected_symbol: str, chain: list[dict]) -> tuple[str, str]:
    if not chain:
        return "NO_CALENDAR", "calendar_missing"

    current = chain[0]["symbol"]
    next_symbol = chain[1]["symbol"] if len(chain) > 1 else "NONE"
    known = {row["symbol"] for row in chain}

    if runtime_symbol == selected_symbol:
        return "MATCH_SELECTOR", "runtime_equals_calendar_selector"

    if runtime_symbol == current:
        return "RUNTIME_CURRENT_NOT_SELECTED", "runtime_on_current_but_selector_differs"

    if runtime_symbol == next_symbol:
        return "RUNTIME_NEXT_NOT_SELECTED", "runtime_on_next_contract"

    if runtime_symbol in known:
        return "RUNTIME_KNOWN_FUTURE_NOT_SELECTED", "runtime_on_known_future_contract"

    return "RUNTIME_UNKNOWN", "runtime_contract_not_in_calendar"

def main() -> None:
    print("=== CONTRACT SELECTOR VS RUNTIME V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"roots={','.join(ROOTS)}")
    print()

    runtime_symbols = [s for s in read_runtime_symbols() if root_for(s) in set(ROOTS)]

    runtime_by_root: dict[str, list[str]] = {}
    for symbol in runtime_symbols:
        runtime_by_root.setdefault(root_for(symbol), []).append(symbol)

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (ROOTS,))
            calendar_rows = [dict(row) for row in cur.fetchall()]

    chain_by_root: dict[str, list[dict]] = {}
    for row in calendar_rows:
        chain_by_root.setdefault(row["root_symbol"], []).append(row)

    print("SELECTOR_RUNTIME_ROWS")
    total = 0

    for root in ROOTS:
        chain = chain_by_root.get(root, [])
        selected_symbol, selector_action, days, selector_reason = choose_calendar_contract(chain)

        runtimes = runtime_by_root.get(root) or ["NONE"]

        current = chain[0]["symbol"] if chain else "NONE"
        next_symbol = chain[1]["symbol"] if len(chain) > 1 else "NONE"

        for runtime_symbol in runtimes:
            if runtime_symbol == "NONE":
                status = "NO_RUNTIME_SYMBOL"
                reason = "runtime_symbol_missing"
            else:
                status, reason = classify_runtime(runtime_symbol, selected_symbol, chain)

            total += 1

            print(
                "SELECTOR_RUNTIME_ROW "
                f"root={root} "
                f"runtime_symbol={runtime_symbol} "
                f"calendar_current={current} "
                f"calendar_next={next_symbol} "
                f"selector_symbol={selected_symbol} "
                f"selector_action={selector_action} "
                f"selector_days_to_current_last_trade={days} "
                f"selector_reason={selector_reason} "
                f"alignment_status={status} "
                f"alignment_reason={reason}"
            )

    print()
    print(f"ROWS={total}")
    print("VERDICT=CONTRACT_SELECTOR_RUNTIME_COMPARED")
    print("CONTRACT_SELECTOR_VS_RUNTIME_V1_OK")

if __name__ == "__main__":
    main()
