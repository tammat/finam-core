from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier


def pct_change(curr: float, prev: float) -> float:
    if prev == 0:
        return 0.0
    return ((curr - prev) / abs(prev)) * 100.0


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    watchlist_drop_pct = float(
        os.getenv("RUNTIME_DRIFT_WATCHLIST_DROP_PCT", "70")
    )

    signal_drop_pct = float(
        os.getenv("RUNTIME_DRIFT_SIGNAL_DROP_PCT", "80")
    )

    stale_snapshot_minutes = float(
        os.getenv("RUNTIME_DRIFT_STALE_SNAPSHOT_MINUTES", "20")
    )

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    created_at,
                    active_signals,
                    active_watchlist,
                    active_positions
                from runtime_state_snapshots
                where state_key = 'runtime_state'
                order by created_at desc
                limit 2
            """)

            rows = cur.fetchall()

    if len(rows) < 2:
        print("RUNTIME_DRIFT_NOT_ENOUGH_DATA", flush=True)
        return 0

    curr = rows[0]
    prev = rows[1]

    curr_ts = curr[0]
    curr_signals = int(curr[1] or 0)
    curr_watchlist = int(curr[2] or 0)
    curr_positions = int(curr[3] or 0)

    prev_signals = int(prev[1] or 0)
    prev_watchlist = int(prev[2] or 0)
    prev_positions = int(prev[3] or 0)

    signal_change = pct_change(curr_signals, prev_signals)
    watchlist_change = pct_change(curr_watchlist, prev_watchlist)

    now = datetime.now(timezone.utc)
    snapshot_age_min = (
        now - curr_ts
    ).total_seconds() / 60.0

    drifts: list[str] = []

    if prev_watchlist > 0 and watchlist_change <= -watchlist_drop_pct:
        drifts.append(
            f"резкое падение watchlist: "
            f"{prev_watchlist} → {curr_watchlist} "
            f"({watchlist_change:.1f}%)"
        )

    if prev_signals > 0 and signal_change <= -signal_drop_pct:
        drifts.append(
            f"резкое падение signals: "
            f"{prev_signals} → {curr_signals} "
            f"({signal_change:.1f}%)"
        )

    if snapshot_age_min >= stale_snapshot_minutes:
        drifts.append(
            f"устаревший runtime snapshot: "
            f"age={snapshot_age_min:.1f} min"
        )

    if curr_watchlist == 0:
        drifts.append("runtime watchlist empty")

    if drifts:
        text = (
            "⚠️ Runtime Drift Detection\n\n"
            f"Snapshot: {curr_ts}\n\n"
            + "\n".join(drifts)
        )

        TelegramNotifier().send(text)

        print(
            f"RUNTIME_DRIFT_DETECTED drifts={len(drifts)}",
            flush=True,
        )

        return 1

    print(
        "RUNTIME_DRIFT_OK "
        f"signals={curr_signals} "
        f"watchlist={curr_watchlist} "
        f"positions={curr_positions}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
