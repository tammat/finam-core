from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import psycopg2


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    row = cur.fetchone()
    return int(row[0] or 0)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            active_signals = scalar(
                cur,
                """
                select count(*)
                from signal_lifecycle
                where state in ('NEW','ACTIVE','TRIGGERED')
                """,
            )

            active_watchlist = scalar(
                cur,
                """
                select count(*)
                from dynamic_watchlist
                where is_active = true
                """,
            )

            active_positions = scalar(
                cur,
                """
                select count(*)
                from real_portfolio_positions
                where coalesce(qty, 0) <> 0
                """,
            )

            payload = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "active_signals": active_signals,
                "active_watchlist": active_watchlist,
                "active_positions": active_positions,
            }

            status = "OK"
            reason = "runtime_state_snapshot_saved"

            cur.execute(
                """
                insert into runtime_state_snapshots (
                    state_key,
                    state_type,
                    active_signals,
                    active_watchlist,
                    active_positions,
                    status,
                    reason,
                    raw_json
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                """,
                (
                    "runtime_state",
                    "snapshot",
                    active_signals,
                    active_watchlist,
                    active_positions,
                    status,
                    reason,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    print(
        "RUNTIME_STATE_SNAPSHOT_OK "
        f"active_signals={active_signals} "
        f"active_watchlist={active_watchlist} "
        f"active_positions={active_positions}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
