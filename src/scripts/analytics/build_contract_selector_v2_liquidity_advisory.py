#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ROOTS = [x.strip().upper() for x in os.getenv("CONTRACT_SELECTOR_ROOTS", "BR,NG").split(",") if x.strip()]
NEXT_VOLUME_MULTIPLIER = float(os.getenv("NEXT_VOLUME_MULTIPLIER", "1.20"))

SQL = """
SELECT
    root_symbol,
    symbol,
    contract_role,
    last_trade_date,
    (last_trade_date - CURRENT_DATE) AS days_to_last_trade
FROM futures_contract_calendar
WHERE root_symbol = ANY(%s)
  AND last_trade_date >= CURRENT_DATE
ORDER BY root_symbol, last_trade_date;
"""

def secid(symbol: str) -> str:
    return symbol.split("@", 1)[0]

def fetch_market_snapshot(secid_value: str) -> dict:
    url = (
        "https://iss.moex.com/iss/engines/futures/markets/forts/"
        f"securities/{secid_value}.json?iss.meta=off"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))

    result = {}

    for block in ("marketdata", "securities"):
        if block not in data:
            continue
        columns = data[block].get("columns") or []
        rows = data[block].get("data") or []
        if not rows:
            continue
        row = dict(zip(columns, rows[0]))
        result.update(row)

    return result

def num(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0

def choose(root: str, current: dict, next_contract: dict | None) -> tuple[str, str, str, dict, dict]:
    if not current:
        return "NONE", "NO_CALENDAR", "calendar_missing", {}, {}

    current_symbol = current["symbol"]

    if not next_contract:
        current_md = fetch_market_snapshot(secid(current_symbol))
        return current_symbol, "SELECT_CURRENT", "no_next_contract", current_md, {}

    next_symbol = next_contract["symbol"]

    current_md = fetch_market_snapshot(secid(current_symbol))
    next_md = fetch_market_snapshot(secid(next_symbol))

    current_volume = num(current_md.get("VOLTODAY") or current_md.get("VALTODAY") or current_md.get("NUMTRADES"))
    next_volume = num(next_md.get("VOLTODAY") or next_md.get("VALTODAY") or next_md.get("NUMTRADES"))

    current_trades = num(current_md.get("NUMTRADES"))
    next_trades = num(next_md.get("NUMTRADES"))

    current_days = int(current["days_to_last_trade"])
    next_days = int(next_contract["days_to_last_trade"])

    if current_days <= 3:
        return next_symbol, "SELECT_NEXT_EXPIRY_PROTECTION", "current_contract_expiring", current_md, next_md

    if next_volume > current_volume * NEXT_VOLUME_MULTIPLIER and next_trades >= current_trades:
        return next_symbol, "SELECT_NEXT_LIQUIDITY", "next_contract_more_liquid", current_md, next_md

    return current_symbol, "SELECT_CURRENT_LIQUIDITY", "current_contract_liquidity_ok", current_md, next_md

def main() -> None:
    print("=== CONTRACT SELECTOR V2 LIQUIDITY ADVISORY ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"roots={','.join(ROOTS)}")
    print(f"next_volume_multiplier={NEXT_VOLUME_MULTIPLIER}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (ROOTS,))
            rows = [dict(x) for x in cur.fetchall()]

    by_root: dict[str, list[dict]] = {}
    for row in rows:
        by_root.setdefault(row["root_symbol"], []).append(row)

    print("LIQUIDITY_ADVISORY_ROWS")

    for root in ROOTS:
        chain = by_root.get(root, [])
        current = chain[0] if chain else {}
        next_contract = chain[1] if len(chain) > 1 else None

        selected, action, reason, current_md, next_md = choose(root, current, next_contract)

        current_symbol = current.get("symbol", "NONE")
        next_symbol = next_contract.get("symbol", "NONE") if next_contract else "NONE"

        print(
            "LIQUIDITY_ROW "
            f"root={root} "
            f"calendar_current={current_symbol} "
            f"calendar_next={next_symbol} "
            f"selected_symbol={selected} "
            f"action={action} "
            f"reason={reason} "
            f"current_days={current.get('days_to_last_trade')} "
            f"next_days={next_contract.get('days_to_last_trade') if next_contract else None} "
            f"current_voltoday={current_md.get('VOLTODAY')} "
            f"next_voltoday={next_md.get('VOLTODAY')} "
            f"current_numtrades={current_md.get('NUMTRADES')} "
            f"next_numtrades={next_md.get('NUMTRADES')}"
        )

    print()
    print("VERDICT=CONTRACT_SELECTOR_V2_LIQUIDITY_ADVISORY_RECORDED")
    print("CONTRACT_SELECTOR_V2_LIQUIDITY_ADVISORY_OK")

if __name__ == "__main__":
    main()
