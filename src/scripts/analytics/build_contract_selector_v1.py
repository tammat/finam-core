#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ROOTS = [x.strip().upper() for x in os.getenv("CONTRACT_SELECTOR_ROOTS", "BR,NG").split(",") if x.strip()]
ENTRY_BLOCK_DAYS = int(os.getenv("CONTRACT_SELECTOR_ENTRY_BLOCK_DAYS", "3"))
WATCH_DAYS = int(os.getenv("CONTRACT_SELECTOR_WATCH_DAYS", "7"))

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

def choose_contract(chain: list[dict]) -> tuple[str, str, int | None, str]:
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

def main() -> None:
    print("=== CONTRACT SELECTOR V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"roots={','.join(ROOTS)}")
    print(f"entry_block_days={ENTRY_BLOCK_DAYS}")
    print(f"watch_days={WATCH_DAYS}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (ROOTS,))
            rows = [dict(x) for x in cur.fetchall()]

    by_root: dict[str, list[dict]] = {}
    for row in rows:
        by_root.setdefault(row["root_symbol"], []).append(row)

    print("CONTRACT_SELECTOR_ROWS")

    for root in ROOTS:
        chain = by_root.get(root, [])
        current = chain[0]["symbol"] if chain else "NONE"
        next_symbol = chain[1]["symbol"] if len(chain) > 1 else "NONE"

        selected, action, days, reason = choose_contract(chain)

        print(
            "SELECTOR_ROW "
            f"root={root} "
            f"calendar_current={current} "
            f"calendar_next={next_symbol} "
            f"selected_symbol={selected} "
            f"days_to_current_last_trade={days} "
            f"action={action} "
            f"reason={reason}"
        )

    print()
    print("VERDICT=CONTRACT_SELECTOR_RECORDED")
    print("CONTRACT_SELECTOR_V1_OK")

if __name__ == "__main__":
    main()
