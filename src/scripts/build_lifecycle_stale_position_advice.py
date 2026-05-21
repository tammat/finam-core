from __future__ import annotations

import argparse
from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.portfolio.lifecycle_stale_position_advisor import (
    LifecycleStalePositionInput,
    build_lifecycle_stale_position_advice,
)
import psycopg
from finam_core.portfolio.lifecycle_stale_position_repository import LifecycleStalePositionRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    database_url = build_psycopg_url()

    sql = """
    SELECT DISTINCT ON (symbol)
        symbol,
        display_name,
        broker_qty,
        lifecycle_qty,
        managed_qty,
        status
    FROM position_state_reconciliation_events
    ORDER BY symbol, created_at DESC
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    high = 0
    medium = 0
    advices = []

    for row in rows:
        advice = build_lifecycle_stale_position_advice(
            LifecycleStalePositionInput(
                symbol=str(row[0]),
                display_name=str(row[1]),
                broker_qty=float(row[2] or 0.0),
                lifecycle_qty=float(row[3] or 0.0),
                managed_qty=float(row[4] or 0.0),
                reconciliation_status=str(row[5]),
            )
        )

        if advice.severity == "HIGH":
            high += 1
        if advice.severity == "MEDIUM":
            medium += 1

        if advice.action != "NO_ACTION":
            advices.append(advice)
            print(
                "LIFECYCLE_STALE_POSITION_ADVICE "
                f"symbol={advice.symbol} "
                f"name={advice.display_name} "
                f"action={advice.action} "
                f"severity={advice.severity} "
                f"block_new_entries={advice.block_new_entries} "
                f"reason={advice.reason}",
                flush=True,
            )

    if args.migrate or args.save:
        repo = LifecycleStalePositionRepository(database_url)
        repo.migrate()

    if args.save:
        repo.save_many(advices)

    print(
        "LIFECYCLE_STALE_POSITION_ADVICE_SUMMARY "
        f"total={len(rows)} high={high} medium={medium}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
