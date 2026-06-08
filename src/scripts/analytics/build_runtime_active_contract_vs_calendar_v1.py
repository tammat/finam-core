#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import re
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

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

def normalize_symbol(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    if "@" in s:
        return s
    return f"{s}@RTSX"

def root_for(symbol: str) -> str:
    u = symbol.upper()
    if u.startswith("BR"):
        return "BR"
    if u.startswith("NG"):
        return "NG"
    return "UNKNOWN"

def read_systemd_symbols() -> list[str]:
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
        env = proc.stdout or ""
    except Exception:
        env = ""

    candidates = []

    patterns = [
        r"ACTIVE_BR_SYMBOLS=([^\s]+)",
        r"ACTIVE_NG_SYMBOLS=([^\s]+)",
        r"ROOT_ACTIVE_BR_SYMBOLS=([^\s]+)",
        r"ROOT_ACTIVE_NG_SYMBOLS=([^\s]+)",
        r"SYMBOLS=([^\s]+)",
        r"--symbols\s+([A-Z0-9@,._-]+)",
    ]

    for pat in patterns:
        m = re.search(pat, env)
        if m:
            candidates.extend(m.group(1).split(","))

    if candidates:
        return sorted({normalize_symbol(x) for x in candidates if x.strip()})

    return sorted({normalize_symbol(x) for x in DEFAULT_RUNTIME_SYMBOLS.split(",") if x.strip()})

def classify(runtime_symbol: str, chain: list[dict]) -> tuple[str, str, str, int | None]:
    if not chain:
        return "NO_CALENDAR", "NONE", "NONE", None

    current = chain[0]
    next_contract = chain[1] if len(chain) > 1 else None

    current_symbol = current["symbol"]
    next_symbol = next_contract["symbol"] if next_contract else "NONE"

    days = None
    for row in chain:
        if row["symbol"] == runtime_symbol:
            days = row["days_to_last_trade"]
            break

    if runtime_symbol == current_symbol:
        return "OK_CURRENT", current_symbol, next_symbol, days

    if next_contract and runtime_symbol == next_symbol:
        return "AHEAD_OF_CURRENT_NEXT", current_symbol, next_symbol, days

    known_symbols = {r["symbol"] for r in chain}
    if runtime_symbol in known_symbols:
        return "KNOWN_FUTURE", current_symbol, next_symbol, days

    return "UNKNOWN_CONTRACT", current_symbol, next_symbol, days

def main() -> None:
    print("=== RUNTIME ACTIVE CONTRACT VS CALENDAR V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    runtime_symbols = read_systemd_symbols()
    print("RUNTIME_SYMBOLS")
    for s in runtime_symbols:
        if root_for(s) in {"BR", "NG"}:
            print(f"RUNTIME_SYMBOL symbol={s} root={root_for(s)}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    by_root: dict[str, list[dict]] = {}
    for row in rows:
        by_root.setdefault(row["root_symbol"], []).append(dict(row))

    print("CONTRACT_ALIGNMENT")
    total = 0
    for symbol in runtime_symbols:
        root = root_for(symbol)
        if root not in {"BR", "NG"}:
            continue

        status, current_symbol, next_symbol, days = classify(symbol, by_root.get(root, []))
        total += 1

        print(
            "ALIGN_ROW "
            f"root={root} "
            f"runtime_symbol={symbol} "
            f"calendar_current={current_symbol} "
            f"calendar_next={next_symbol} "
            f"runtime_days_to_last_trade={days} "
            f"status={status}"
        )

    print()
    print(f"ROWS={total}")
    print("VERDICT=RUNTIME_ACTIVE_CONTRACT_CALENDAR_COMPARED")
    print("RUNTIME_ACTIVE_CONTRACT_VS_CALENDAR_V1_OK")

if __name__ == "__main__":
    main()
