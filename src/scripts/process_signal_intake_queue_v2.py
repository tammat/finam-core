from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LOCK_ID = 941903129
LIFECYCLE_TIMEOUT_SECONDS = max(
    60,
    int(os.getenv("SIGNAL_LIFECYCLE_TIMEOUT_SECONDS", "300")),
)
TERMINAL_SIGNAL_STATUSES = {
    "ACCEPTED", "RISK_ACCEPTED", "RISK_REJECTED", "FILLED", "CLOSED", "REJECTED"
}


def main() -> int:
    completed = failed = waiting = recovered = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("VERDICT=SIGNAL_INTAKE_QUEUE_ALREADY_RUNNING")
                return 0
            cursor.execute("""SELECT batch_size,retry_seconds,stale_running_minutes,max_attempts
                FROM analytics.signal_intake_policy_v2 WHERE enabled
                ORDER BY updated_at DESC LIMIT 1""")
            policy = cursor.fetchone()
            if policy is None:
                raise RuntimeError("SIGNAL_INTAKE_POLICY_MISSING")

            cursor.execute("""UPDATE analytics.signal_intake_queue_v2
                SET status_code='WAITING',next_attempt_at=clock_timestamp(),
                    failure_code='RECOVERED_STALE_RUNNING',updated_at=clock_timestamp()
                WHERE status_code='RUNNING'
                  AND started_at < clock_timestamp()-(%s * interval '1 minute')""",
                (policy["stale_running_minutes"],))
            recovered = cursor.rowcount

            cursor.execute("""WITH picked AS (
                  SELECT signal_row_id FROM analytics.signal_intake_queue_v2
                  WHERE status_code IN ('QUEUED','WAITING')
                    AND next_attempt_at<=clock_timestamp()
                  ORDER BY priority,next_attempt_at,enqueued_at
                  FOR UPDATE SKIP LOCKED LIMIT %s)
                UPDATE analytics.signal_intake_queue_v2 q
                SET status_code='RUNNING',attempts=q.attempts+1,
                    started_at=clock_timestamp(),updated_at=clock_timestamp()
                FROM picked WHERE q.signal_row_id=picked.signal_row_id
                RETURNING q.signal_row_id,q.signal_id,q.attempts""", (policy["batch_size"],))
            items = cursor.fetchall()

            for item in items:
                cursor.execute("""SELECT symbol,side,strategy,status,created_at,
                        EXTRACT(EPOCH FROM (clock_timestamp()-created_at)) AS age_seconds
                    FROM public.signals WHERE id=%s""", (item["signal_row_id"],))
                signal = cursor.fetchone()
                if signal is None:
                    cursor.execute("""UPDATE analytics.signal_intake_queue_v2
                        SET status_code='FAILED',failure_code='SIGNAL_ROW_MISSING',
                            finished_at=clock_timestamp(),updated_at=clock_timestamp()
                        WHERE signal_row_id=%s""", (item["signal_row_id"],))
                    failed += 1
                    continue
                missing = [name for name in ("symbol", "side", "strategy") if not signal[name]]
                if missing:
                    cursor.execute("""UPDATE analytics.signal_intake_queue_v2
                        SET status_code='FAILED',failure_code=%s,
                            finished_at=clock_timestamp(),updated_at=clock_timestamp()
                        WHERE signal_row_id=%s""",
                        ("SIGNAL_FIELDS_MISSING:" + ",".join(missing), item["signal_row_id"]))
                    failed += 1
                    continue
                signal_status = str(signal["status"] or "NEW").upper()
                if signal_status in TERMINAL_SIGNAL_STATUSES:
                    cursor.execute("""UPDATE analytics.signal_intake_queue_v2
                        SET status_code='COMPLETE',outcome_code=%s,failure_code=NULL,
                            finished_at=clock_timestamp(),updated_at=clock_timestamp()
                        WHERE signal_row_id=%s""",
                        ("SIGNAL_" + signal_status, item["signal_row_id"]))
                    completed += 1
                elif (
                    item["attempts"] >= policy["max_attempts"]
                    or float(signal["age_seconds"] or 0.0) >= LIFECYCLE_TIMEOUT_SECONDS
                ):
                    cursor.execute("""UPDATE public.signals
                        SET status='RISK_REJECTED',
                            rejection_reason=COALESCE(rejection_reason,'signal_lifecycle_timeout')
                        WHERE id=%s AND COALESCE(status,'NEW') NOT IN
                            ('ACCEPTED','RISK_ACCEPTED','RISK_REJECTED','FILLED','CLOSED','REJECTED')""",
                        (item["signal_row_id"],))
                    cursor.execute("""UPDATE analytics.signal_intake_queue_v2
                        SET status_code='FAILED',failure_code='SIGNAL_LIFECYCLE_TIMEOUT',
                            finished_at=clock_timestamp(),updated_at=clock_timestamp()
                        WHERE signal_row_id=%s""", (item["signal_row_id"],))
                    failed += 1
                else:
                    cursor.execute("""UPDATE analytics.signal_intake_queue_v2
                        SET status_code='WAITING',outcome_code=%s,
                            next_attempt_at=clock_timestamp()+(%s * interval '1 second'),
                            updated_at=clock_timestamp()
                        WHERE signal_row_id=%s""",
                        ("WAITING_SIGNAL_" + signal_status, policy["retry_seconds"], item["signal_row_id"]))
                    waiting += 1

    print(f"completed={completed}")
    print(f"waiting={waiting}")
    print(f"failed={failed}")
    print(f"recovered={recovered}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("live_allowed=0")
    print("VERDICT=SIGNAL_INTAKE_QUEUE_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
