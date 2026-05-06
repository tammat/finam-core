# -*- coding: utf-8 -*-
"""
Управление категориями позиций.
Русский комментарий: добавляет и переносит позиции между intraday/swing/long_term.
"""

from __future__ import annotations

import argparse
import os
import psycopg2


VALID = {"intraday", "swing", "long_term"}


def conn():
    return psycopg2.connect(os.getenv("DATABASE_URL", "dbname=finam user=alex host=localhost"))


def flags(horizon: str):
    if horizon == "intraday":
        return True, True, True
    if horizon == "swing":
        return False, True, True
    if horizon == "long_term":
        return False, False, False
    raise ValueError(f"bad horizon: {horizon}")


def upsert(symbol: str, horizon: str, comment: str):
    if horizon not in VALID:
        raise SystemExit(f"bad horizon: {horizon}")

    allow_exit, allow_trailing, allow_buy = flags(horizon)

    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT horizon, enabled FROM position_intents WHERE symbol=%s", (symbol,))
        old = cur.fetchone()

        cur.execute(
            """
            INSERT INTO position_intents
            (symbol, horizon, allow_intraday_exit, allow_trailing, allow_new_buy, enabled, comment)
            VALUES (%s,%s,%s,%s,%s,true,%s)
            ON CONFLICT (symbol) DO UPDATE SET
                horizon=EXCLUDED.horizon,
                allow_intraday_exit=EXCLUDED.allow_intraday_exit,
                allow_trailing=EXCLUDED.allow_trailing,
                allow_new_buy=EXCLUDED.allow_new_buy,
                enabled=true,
                comment=EXCLUDED.comment,
                updated_at=now()
            """,
            (symbol, horizon, allow_exit, allow_trailing, allow_buy, comment),
        )

        cur.execute(
            """
            INSERT INTO position_intent_history
            (symbol, old_horizon, new_horizon, old_enabled, new_enabled, comment)
            VALUES (%s,%s,%s,%s,true,%s)
            """,
            (symbol, old[0] if old else None, horizon, old[1] if old else None, comment),
        )

    print(f"OK {symbol} -> {horizon}")


def disable(symbol: str, comment: str):
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT horizon, enabled FROM position_intents WHERE symbol=%s", (symbol,))
        old = cur.fetchone()

        cur.execute(
            "UPDATE position_intents SET enabled=false, updated_at=now(), comment=%s WHERE symbol=%s",
            (comment, symbol),
        )

        cur.execute(
            """
            INSERT INTO position_intent_history
            (symbol, old_horizon, new_horizon, old_enabled, new_enabled, comment)
            VALUES (%s,%s,%s,%s,false,%s)
            """,
            (symbol, old[0] if old else None, old[0] if old else "swing", old[1] if old else None, comment),
        )

    print(f"OK disabled {symbol}")


def list_rows():
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, horizon, allow_intraday_exit, allow_trailing, allow_new_buy, enabled, comment
            FROM position_intents
            ORDER BY horizon, symbol
            """
        )
        for r in cur.fetchall():
            print("\t".join(map(str, r)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["set", "disable", "list"])
    p.add_argument("--symbol")
    p.add_argument("--horizon", choices=sorted(VALID))
    p.add_argument("--comment", default="")
    a = p.parse_args()

    if a.cmd == "set":
        upsert(a.symbol, a.horizon, a.comment)
    elif a.cmd == "disable":
        disable(a.symbol, a.comment)
    else:
        list_rows()


if __name__ == "__main__":
    main()
