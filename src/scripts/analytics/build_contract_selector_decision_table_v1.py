#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ROOTS = [
    x.strip().upper()
    for x in os.getenv("CONTRACT_SELECTOR_ROOTS", "BR,NG").split(",")
    if x.strip()
]

ENTRY_BLOCK_DAYS = int(os.getenv("CONTRACT_SELECTOR_ENTRY_BLOCK_DAYS", "3"))
WATCH_DAYS = int(os.getenv("CONTRACT_SELECTOR_WATCH_DAYS", "7"))
NEXT_VOLUME_MULTIPLIER = float(os.getenv("NEXT_VOLUME_MULTIPLIER", "1.20"))

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
    u = symbol.upper()
    if u.startswith("BR"):
        return "BR"
    if u.startswith("NG"):
        return "NG"
    return "UNKNOWN"

def secid(symbol: str) -> str:
    return symbol.split("@", 1)[0]

def num(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0

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
        m = re.search(pattern, env_text)
        if m:
            candidates.extend(m.group(1).split(","))

    if not candidates:
        candidates = DEFAULT_RUNTIME_SYMBOLS.split(",")

    return sorted({normalize_symbol(x) for x in candidates if x.strip()})

def fetch_market_snapshot(symbol: str) -> dict:
    secid_value = secid(symbol)
    url = (
        "https://iss.moex.com/iss/engines/futures/markets/forts/"
        f"securities/{secid_value}.json?iss.meta=off"
    )

    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}

    result: dict = {}
    for block in ("marketdata", "securities"):
        if block not in data:
            continue
        columns = data[block].get("columns") or []
        rows = data[block].get("data") or []
        if not rows:
            continue
        result.update(dict(zip(columns, rows[0])))

    return result

def calendar_selector(chain: list[dict]) -> tuple[str, str, int | None, str]:
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

def liquidity_selector(chain: list[dict]) -> tuple[str, str, str, dict, dict]:
    if not chain:
        return "NONE", "NO_CALENDAR", "calendar_missing", {}, {}

    current = chain[0]
    next_contract = chain[1] if len(chain) > 1 else None

    current_symbol = current["symbol"]
    current_md = fetch_market_snapshot(current_symbol)

    if not next_contract:
        return current_symbol, "SELECT_CURRENT", "no_next_contract", current_md, {}

    next_symbol = next_contract["symbol"]
    next_md = fetch_market_snapshot(next_symbol)

    current_volume = num(current_md.get("VOLTODAY") or current_md.get("VALTODAY") or current_md.get("NUMTRADES"))
    next_volume = num(next_md.get("VOLTODAY") or next_md.get("VALTODAY") or next_md.get("NUMTRADES"))

    current_trades = num(current_md.get("NUMTRADES"))
    next_trades = num(next_md.get("NUMTRADES"))

    days = int(current["days_to_last_trade"])

    if days <= ENTRY_BLOCK_DAYS:
        return next_symbol, "SELECT_NEXT_EXPIRY_PROTECTION", "current_contract_expiring", current_md, next_md

    if next_volume > current_volume * NEXT_VOLUME_MULTIPLIER and next_trades >= current_trades:
        return next_symbol, "SELECT_NEXT_LIQUIDITY", "next_contract_more_liquid", current_md, next_md

    return current_symbol, "SELECT_CURRENT_LIQUIDITY", "current_contract_liquidity_ok", current_md, next_md

def decide(
    runtime_symbol: str,
    calendar_current: str,
    calendar_next: str,
    selector_calendar: str,
    selector_liquidity: str,
    days_to_current: int | None,
) -> tuple[str, str, str]:
    if calendar_current == "NONE":
        return "CALENDAR_MISSING", "REVIEW", "calendar_missing"

    if runtime_symbol == "NONE":
        return "NO_RUNTIME_SYMBOL", "REVIEW", "runtime_symbol_missing"

    if days_to_current is not None and days_to_current <= ENTRY_BLOCK_DAYS:
        return "ROLLOVER_REQUIRED", "STOP_NEW_ENTRIES", "current_contract_expiring"

    if runtime_symbol == selector_liquidity:
        return "RUNTIME_MATCHES_SELECTOR", "KEEP", "runtime_equals_liquidity_selector"

    if runtime_symbol == calendar_next and selector_liquidity == calendar_current:
        return "RUNTIME_AHEAD_BUT_LESS_LIQUID", "REVIEW", "runtime_on_next_while_current_more_liquid"

    if runtime_symbol == calendar_next and selector_liquidity == calendar_next:
        return "RUNTIME_AHEAD_BUT_MORE_LIQUID", "KEEP", "runtime_on_next_and_next_more_liquid"

    if runtime_symbol == selector_calendar and selector_calendar != selector_liquidity:
        return "RUNTIME_MATCHES_CALENDAR_NOT_LIQUIDITY", "REVIEW", "calendar_and_liquidity_disagree"

    return "REVIEW_REQUIRED", "REVIEW", "runtime_selector_mismatch"

def main() -> None:
    print("=== CONTRACT SELECTOR DECISION TABLE V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"roots={','.join(ROOTS)}")
    print(f"entry_block_days={ENTRY_BLOCK_DAYS}")
    print(f"watch_days={WATCH_DAYS}")
    print(f"next_volume_multiplier={NEXT_VOLUME_MULTIPLIER}")
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

    print("DECISION_ROWS")
    total = 0

    for root in ROOTS:
        chain = chain_by_root.get(root, [])
        current = chain[0]["symbol"] if chain else "NONE"
        next_symbol = chain[1]["symbol"] if len(chain) > 1 else "NONE"
        days = chain[0]["days_to_last_trade"] if chain else None

        selector_calendar, selector_calendar_action, _, selector_calendar_reason = calendar_selector(chain)
        selector_liquidity, selector_liquidity_action, selector_liquidity_reason, current_md, next_md = liquidity_selector(chain)

        runtimes = runtime_by_root.get(root) or ["NONE"]

        for runtime_symbol in runtimes:
            decision, action, reason = decide(
                runtime_symbol=runtime_symbol,
                calendar_current=current,
                calendar_next=next_symbol,
                selector_calendar=selector_calendar,
                selector_liquidity=selector_liquidity,
                days_to_current=days,
            )
            total += 1

            print(
                "DECISION_ROW "
                f"root={root} "
                f"runtime_symbol={runtime_symbol} "
                f"calendar_current={current} "
                f"calendar_next={next_symbol} "
                f"selector_calendar={selector_calendar} "
                f"selector_calendar_action={selector_calendar_action} "
                f"selector_liquidity={selector_liquidity} "
                f"selector_liquidity_action={selector_liquidity_action} "
                f"days_to_current_last_trade={days} "
                f"current_voltoday={current_md.get('VOLTODAY')} "
                f"next_voltoday={next_md.get('VOLTODAY')} "
                f"current_numtrades={current_md.get('NUMTRADES')} "
                f"next_numtrades={next_md.get('NUMTRADES')} "
                f"decision={decision} "
                f"action={action} "
                f"reason={reason} "
                f"selector_calendar_reason={selector_calendar_reason} "
                f"selector_liquidity_reason={selector_liquidity_reason}"
            )

    print()
    print(f"ROWS={total}")
    print("VERDICT=CONTRACT_SELECTOR_DECISION_TABLE_RECORDED")
    print("CONTRACT_SELECTOR_DECISION_TABLE_V1_OK")

if __name__ == "__main__":
    main()
