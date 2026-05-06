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
ROLES = {"core", "hedge", "speculative", "watch_only", "reduce_only"}


def conn():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return psycopg2.connect(database_url)


def flags(horizon: str, trade_role: str):
    if horizon == "intraday":
        allow_exit, allow_trailing, allow_buy = True, True, True
    elif horizon == "swing":
        allow_exit, allow_trailing, allow_buy = False, True, True
    elif horizon == "long_term":
        allow_exit, allow_trailing, allow_buy = False, False, False
    else:
        raise ValueError(f"bad horizon: {horizon}")

    allow_reduce = True
    allow_increase = allow_buy

    if trade_role == "watch_only":
        allow_exit = False
        allow_trailing = False
        allow_buy = False
        allow_reduce = False
        allow_increase = False

    if trade_role == "reduce_only":
        allow_exit = False
        allow_buy = False
        allow_reduce = True
        allow_increase = False

    if trade_role == "hedge":
        allow_trailing = True

    return allow_exit, allow_trailing, allow_buy, allow_reduce, allow_increase


def upsert(symbol: str, horizon: str, trade_role: str, comment: str):
    if horizon not in VALID:
        raise SystemExit(f"bad horizon: {horizon}")
    if trade_role not in ROLES:
        raise SystemExit(f"bad trade_role: {trade_role}")

    allow_exit, allow_trailing, allow_buy, allow_reduce, allow_increase = flags(horizon, trade_role)

    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT horizon, enabled, trade_role, allow_reduce, allow_increase FROM position_intents WHERE symbol=%s", (symbol,))
        old = cur.fetchone()

        cur.execute(
            """
            INSERT INTO position_intents
            (symbol, horizon, trade_role, allow_intraday_exit, allow_trailing,
             allow_new_buy, allow_reduce, allow_increase, enabled, comment)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,true,%s)
            ON CONFLICT (symbol) DO UPDATE SET
                horizon=EXCLUDED.horizon,
                trade_role=EXCLUDED.trade_role,
                allow_intraday_exit=EXCLUDED.allow_intraday_exit,
                allow_trailing=EXCLUDED.allow_trailing,
                allow_new_buy=EXCLUDED.allow_new_buy,
                allow_reduce=EXCLUDED.allow_reduce,
                allow_increase=EXCLUDED.allow_increase,
                enabled=true,
                comment=EXCLUDED.comment,
                updated_at=now()
            """,
            (symbol, horizon, trade_role, allow_exit, allow_trailing, allow_buy, allow_reduce, allow_increase, comment),
        )

        cur.execute(
            """
            INSERT INTO position_intent_history
            (symbol, old_horizon, new_horizon, old_enabled, new_enabled,
             old_trade_role, new_trade_role, old_allow_reduce, new_allow_reduce,
             old_allow_increase, new_allow_increase, comment)
            VALUES (%s,%s,%s,%s,true,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                symbol,
                old[0] if old else None,
                horizon,
                old[1] if old else None,
                old[2] if old else None,
                trade_role,
                old[3] if old else None,
                allow_reduce,
                old[4] if old else None,
                allow_increase,
                comment,
            ),
        )

    print(f"OK {symbol} -> {horizon}")


def disable(symbol: str, comment: str):
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT horizon, enabled, trade_role, allow_reduce, allow_increase FROM position_intents WHERE symbol=%s", (symbol,))
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
            SELECT symbol, horizon, trade_role, allow_intraday_exit, allow_trailing,
                   allow_new_buy, allow_reduce, allow_increase, enabled, comment
            FROM position_intents
            ORDER BY horizon, trade_role, symbol
            """
        )
        for r in cur.fetchall():
            print("\t".join(map(str, r)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["set", "disable", "list"])
    p.add_argument("--symbol")
    p.add_argument("--horizon", choices=sorted(VALID))
    p.add_argument("--role", default="core", choices=sorted(ROLES))
    p.add_argument("--comment", default="")
    a = p.parse_args()

    if a.cmd == "set":
        upsert(a.symbol, a.horizon, a.role, a.comment)
    elif a.cmd == "disable":
        disable(a.symbol, a.comment)
    else:
        list_rows()


if __name__ == "__main__":
    main()
