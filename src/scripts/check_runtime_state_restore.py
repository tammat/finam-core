from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    created_at,
                    active_signals,
                    active_watchlist,
                    active_positions,
                    status,
                    reason
                from runtime_state_snapshots
                where state_key = 'runtime_state'
                order by created_at desc
                limit 1
                """
            )
            row = cur.fetchone()

    if row is None:
        print("RUNTIME_STATE_RESTORE_EMPTY", flush=True)
        return 0

    print(
        "RUNTIME_STATE_RESTORE_OK "
        f"created_at={row[0]} "
        f"active_signals={row[1]} "
        f"active_watchlist={row[2]} "
        f"active_positions={row[3]} "
        f"status={row[4]} "
        f"reason={row[5]}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
