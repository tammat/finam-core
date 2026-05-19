from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    symbol = os.getenv("FIRST_REAL_ORDER_SYMBOL", "SBER@MISX")
    max_qty = float(os.getenv("FIRST_REAL_ORDER_MAX_QTY", "1"))
    max_value = float(os.getenv("FIRST_REAL_ORDER_MAX_VALUE", "3000"))

    enabled = os.getenv("REAL_BUY_EXECUTION_ENABLED", "0") == "1"
    kill_switch = os.getenv("REAL_BUY_KILL_SWITCH", "1") == "1"
    wiring = os.getenv("REAL_BUY_CLIENT_WIRING_CONFIRMED", "0") == "1"

    problems: list[str] = []

    if symbol != "SBER@MISX":
        problems.append(f"symbol_not_allowed_for_first_order:{symbol}")

    if max_qty > 1:
        problems.append(f"max_qty_too_high:{max_qty}")

    if max_value > 3000:
        problems.append(f"max_value_too_high:{max_value}")

    if not enabled:
        problems.append("REAL_BUY_EXECUTION_ENABLED!=1")

    if kill_switch:
        problems.append("REAL_BUY_KILL_SWITCH=1")

    if not wiring:
        problems.append("REAL_BUY_CLIENT_WIRING_CONFIRMED!=1")

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select exists (
                    select 1
                    from runtime_risk_freeze
                    where is_active = true
                )
            """)
            if bool(cur.fetchone()[0]):
                problems.append("runtime_risk_freeze_active")

    if problems:
        print(
            "FIRST_REAL_ORDER_CHECK_BLOCKED "
            + ";".join(problems),
            flush=True,
        )
        return 1

    print(
        "FIRST_REAL_ORDER_CHECK_OK "
        f"symbol={symbol} max_qty={max_qty} max_value={max_value}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
