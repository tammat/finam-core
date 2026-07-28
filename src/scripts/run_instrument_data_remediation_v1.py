from __future__ import annotations

import os
import socket
from datetime import timedelta

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LOCK_ID = 941903132
ACTIONS = ("VERIFY_SPEC", "COLLECT_DATA", "COLLECT_LIQUIDITY", "MONITOR_ROLL")


def ensure_watch(cursor, symbol: str, reason: str) -> None:
    cursor.execute(
        """INSERT INTO public.market_data_watch_universe(symbol,asset_group,timeframe,is_enabled,reason)
           VALUES(%s,'REMEDIATION','M1',true,%s)
           ON CONFLICT(symbol) DO UPDATE SET is_enabled=true,reason=excluded.reason""",
        (symbol, reason),
    )


def ready(cursor, action: str, symbol: str) -> tuple[bool, str]:
    if action == "VERIFY_SPEC":
        if not symbol.endswith("@RTSX"):
            return True, "SPEC_NOT_REQUIRED"
        cursor.execute("SELECT EXISTS(SELECT 1 FROM analytics.market_contract_spec_v1 WHERE symbol=%s AND is_active) AS ready", (symbol,))
        return bool(cursor.fetchone()["ready"]), "SPEC_READY"
    if action == "COLLECT_DATA":
        ensure_watch(cursor, symbol, "INSTRUMENT_DATA_REMEDIATION_V1")
        cursor.execute("""SELECT count(*)>=5000 AND max(ts)>=clock_timestamp()-interval '72 hours' AS ready
                          FROM public.market_bars WHERE symbol=%s AND timeframe='M5'
                            AND source NOT IN ('unknown','synthetic_futures_backfill_v1')""", (symbol,))
        return bool(cursor.fetchone()["ready"]), "DATA_READY"
    if action == "COLLECT_LIQUIDITY":
        ensure_watch(cursor, symbol, "INSTRUMENT_LIQUIDITY_REMEDIATION_V1")
        cursor.execute("""SELECT coalesce(sum(snapshot_count),0)>=100 AS ready
                          FROM analytics.market_microstructure_aggregate_v1
                          WHERE symbol=%s AND bucket_ts>=clock_timestamp()-interval '7 days'
                            AND avg_best_bid>0 AND avg_best_ask>=avg_best_bid""", (symbol,))
        return bool(cursor.fetchone()["ready"]), "LIQUIDITY_READY"
    cursor.execute("""SELECT EXISTS(SELECT 1 FROM analytics.futures_roll_decision_v1
                      WHERE %s IN(current_symbol,next_symbol,selected_symbol)
                        AND selected_symbol IS NOT NULL) AS ready""", (symbol,))
    return bool(cursor.fetchone()["ready"]), "ROLL_READY"


def main() -> int:
    owner = f"{socket.gethostname()}:{os.getpid()}"
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
            q.execute("SELECT pg_try_advisory_lock(%s) locked", (LOCK_ID,))
            if not q.fetchone()["locked"]:
                print("VERDICT=INSTRUMENT_REMEDIATION_ALREADY_RUNNING")
                return 0
            q.execute("""SELECT queue_id,symbol,action_code,attempt_count,max_attempts
                         FROM analytics.instrument_scout_queue_v1
                         WHERE action_code=ANY(%s) AND status_code IN ('PENDING','RETRY')
                           AND next_attempt_at<=clock_timestamp()
                           AND (lease_expires_at IS NULL OR lease_expires_at<clock_timestamp())
                         ORDER BY priority DESC,created_at LIMIT 25 FOR UPDATE SKIP LOCKED""", (list(ACTIONS),))
            rows = q.fetchall()
            completed = 0
            for row in rows:
                q.execute("SAVEPOINT instrument_remediation_item")
                q.execute("""UPDATE analytics.instrument_scout_queue_v1 SET status_code='RUNNING',
                             lease_owner=%s,lease_expires_at=clock_timestamp()+interval '3 minutes',updated_at=clock_timestamp()
                             WHERE queue_id=%s""", (owner, row["queue_id"]))
                try:
                    is_ready, reason = ready(q, row["action_code"], row["symbol"])
                    attempts = row["attempt_count"] + 1
                    terminal = is_ready or attempts >= row["max_attempts"]
                    status = "COMPLETE" if is_ready else "BLOCKED" if terminal else "RETRY"
                    delay = min(360, 10 * (2 ** min(attempts - 1, 5)))
                    q.execute("""UPDATE analytics.instrument_scout_queue_v1 SET status_code=%s,
                      attempt_count=%s,last_checked_at=clock_timestamp(),last_error_code=%s,
                      next_attempt_at=clock_timestamp()+(%s*interval '1 minute'),lease_owner=NULL,lease_expires_at=NULL,
                      completed_at=CASE WHEN %s='COMPLETE' THEN clock_timestamp() ELSE completed_at END,
                      updated_at=clock_timestamp() WHERE queue_id=%s""",
                      (status, attempts, None if is_ready else f"WAITING_{reason}", delay, status, row["queue_id"]))
                    completed += int(is_ready)
                    q.execute("RELEASE SAVEPOINT instrument_remediation_item")
                except Exception as exc:
                    q.execute("ROLLBACK TO SAVEPOINT instrument_remediation_item")
                    q.execute("""UPDATE analytics.instrument_scout_queue_v1 SET status_code='RETRY',
                      attempt_count=attempt_count+1,last_checked_at=clock_timestamp(),last_error_code=%s,
                      next_attempt_at=clock_timestamp()+interval '30 minutes',lease_owner=NULL,lease_expires_at=NULL,
                      updated_at=clock_timestamp() WHERE queue_id=%s""", (type(exc).__name__, row["queue_id"]))
                    q.execute("RELEASE SAVEPOINT instrument_remediation_item")
            print(f"claimed={len(rows)} completed={completed}")
            print("VERDICT=INSTRUMENT_DATA_REMEDIATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
