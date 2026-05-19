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
            cur.execute("""
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
            """)
            snapshot = cur.fetchone()

            if snapshot is None:
                print("RUNTIME_STATE_RESTORE_EMPTY", flush=True)
                return 0

            cur.execute("""
                select count(*)
                from signal_lifecycle
                where state in ('NEW','ACTIVE','TRIGGERED')
            """)
            current_active_signals = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from dynamic_watchlist
                where is_active = true
            """)
            current_watchlist = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*)
                from real_portfolio_positions
                where coalesce(qty, 0) <> 0
            """)
            current_positions = int(cur.fetchone()[0] or 0)

    print(
        "RUNTIME_STATE_RESTORE_CHECK "
        f"snapshot_at={snapshot[0]} "
        f"snapshot_active_signals={snapshot[1]} "
        f"current_active_signals={current_active_signals} "
        f"snapshot_watchlist={snapshot[2]} "
        f"current_watchlist={current_watchlist} "
        f"snapshot_positions={snapshot[3]} "
        f"current_positions={current_positions} "
        f"status={snapshot[4]} "
        f"reason={snapshot[5]}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
