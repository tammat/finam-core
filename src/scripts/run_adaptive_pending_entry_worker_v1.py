#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import Bar
from finam_core.execution.adaptive_pending_entry_v1 import evaluate_pending_entry_v1


def main() -> int:
    now = datetime.now(timezone.utc)
    with psycopg2.connect(os.getenv("DATABASE_URL", "postgresql:///finam_core")) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext('adaptive_pending_entry_worker_v1'))")
            cur.execute("""UPDATE analytics.entry_exit_pending_entry_v1
                           SET status='EXPIRED',decision_reason='READY_NOT_CONSUMED_IN_15_MIN',
                               updated_at=clock_timestamp()
                           WHERE status='READY' AND resolved_at < clock_timestamp()-interval '15 minutes'""")
            cur.execute("""SELECT * FROM analytics.entry_exit_pending_entry_v1
                           WHERE status='PENDING' ORDER BY signal_ts,pending_id
                           FOR UPDATE SKIP LOCKED""")
            rows = cur.fetchall()
            for row in rows:
                delta = timedelta(minutes=1 if row["timeframe"] == "M1" else 5)
                cur.execute("""SELECT open::float8,high::float8,low::float8,close::float8
                               FROM market_bars
                               WHERE symbol=%s AND timeframe=%s AND ts>%s AND ts<=%s
                               ORDER BY ts LIMIT 3""",
                            (row["symbol_code"],row["timeframe"],row["signal_ts"],now-delta))
                bars = [Bar(float(item["high"]),float(item["low"]),float(item["close"]),
                            float(item["open"])) for item in cur.fetchall()]
                decision = evaluate_pending_entry_v1(
                    mode=row["entry_mode"],side=row["side_code"],
                    signal_price=float(row["signal_price"]),atr=float(row["atr"]),bars=bars)
                if decision.status == "PENDING":
                    continue
                cur.execute("""UPDATE analytics.entry_exit_pending_entry_v1
                               SET status=%s,decision_reason=%s,resolved_entry_price=%s,
                                   resolved_at=clock_timestamp(),updated_at=clock_timestamp()
                               WHERE pending_id=%s""",
                            (decision.status,decision.reason,decision.entry_price,row["pending_id"]))
            print(f"adaptive_pending_checked={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
