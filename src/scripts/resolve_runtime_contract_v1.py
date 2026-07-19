from __future__ import annotations

import argparse
import os

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, choices=("BR", "NG"))
    args = parser.parse_args()
    with psycopg2.connect(DB) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT d.selected_symbol
                   FROM analytics.futures_roll_decision_v1 d
                   JOIN public.futures_contract_calendar c
                     ON c.symbol=d.selected_symbol AND c.root_symbol=d.root_symbol
                   WHERE d.root_symbol=%s
                     AND c.last_trade_date>=current_date
                     AND d.created_at>=clock_timestamp()-interval '24 hours'
                   ORDER BY d.created_at DESC LIMIT 1""",
                (args.root,),
            )
            row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"ACTIVE_CONTRACT_DECISION_MISSING_OR_STALE:{args.root}")
    print(str(row[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
