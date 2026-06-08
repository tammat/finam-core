#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ENTRY_BLOCK_DAYS = int(os.getenv("ROLLOVER_ENTRY_BLOCK_DAYS", "3"))
WATCH_DAYS = int(os.getenv("ROLLOVER_WATCH_DAYS", "7"))

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
WHERE root_symbol IN ('BR','NG')
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

def advisory_for(runtime_symbol: str, chain: list[dict]) -> tuple[str, str, str, int | None, str]:
    if not chain:
        return "NO_CALENDAR", "NONE", "NONE", None, "calendar_missing"

    current = chain[0]
    next_contract = chain[1] if len(chain) > 1 else None

    current_symbol = current["symbol"]
    next_symbol = next_contract["symbol"] if next_contract else "NONE"

    runtime_row = None
    for row in chain:
        if row["symbol"] == runtime_symbol:
            runtime_row = row
            break

    if runtime_row is None:
        return "UNKNOWN_CONTRACT", current_symbol, next_symbol, None, "runtime_contract_not_in_calendar"

    days = runtime_row["days_to_last_trade"]

    if days is not None and days <= ENTRY_BLOCK_DAYS:
        return "STOP_NEW_ENTRIES", current_symbol, next_symbol, days, "runtime_contract_expiring"

    if runtime_symbol == current_symbol:
        if days is not None and days <= WATCH_DAYS:
            return "ROLLOVER_WATCH", current_symbol, next_symbol, days, "current_contract_near_expiry"
        return "KEEP_CURRENT", current_symbol, next_symbol, days, "runtime_matches_calendar_current"

    if next_contract and runtime_symbol == next_symbol:
        return "TRADE_NEXT", current_symbol, next_symbol, days, "runtime_already_on_next_contract"

    known_symbols = {row["symbol"] for row in chain}
    if runtime_symbol in known_symbols:
        return "TRADE_KNOWN_FUTURE", current_symbol, next_symbol, days, "runtime_known_future_contract"

    return "UNKNOWN_CONTRACT", current_symbol, next_symbol, days, "runtime_contract_not_in_calendar"

def main() -> None:
    print("=== CONTRACT ROLLOVER ADVISORY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"entry_block_days={ENTRY_BLOCK_DAYS}")
    print(f"watch_days={WATCH_DAYS}")
    print()

    runtime_symbols = [s for s in read_runtime_symbols() if root_for(s) in {"BR", "NG"}]

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            calendar_rows = [dict(row) for row in cur.fetchall()]

    by_root: dict[str, list[dict]] = {}
    for row in calendar_rows:
        by_root.setdefault(row["root_symbol"], []).append(row)

    print("ROLLOVER_ADVISORY_ROWS")
    total = 0

    for runtime_symbol in runtime_symbols:
        root = root_for(runtime_symbol)
        action, current_symbol, next_symbol, days, reason = advisory_for(
            runtime_symbol,
            by_root.get(root, []),
        )
        total += 1

        print(
            "ADVISORY_ROW "
            f"root={root} "
            f"runtime_symbol={runtime_symbol} "
            f"calendar_current={current_symbol} "
            f"calendar_next={next_symbol} "
            f"days_to_last_trade={days} "
            f"action={action} "
            f"reason={reason}"
        )

    print()
    print(f"ROWS={total}")
    print("VERDICT=CONTRACT_ROLLOVER_ADVISORY_RECORDED")
    print("CONTRACT_ROLLOVER_ADVISORY_V1_OK")

if __name__ == "__main__":
    main()
