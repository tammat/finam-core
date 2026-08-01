from __future__ import annotations

import os
import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(184005)")
            if not cursor.fetchone()[0]:
                print("admissions_maintenance=already_running")
                return 0
            cursor.execute("""WITH ranked AS (
                SELECT admission_id,row_number() OVER (
                  PARTITION BY symbol,coalesce(oos_request->>'paper_strategy_code',''),
                    coalesce(oos_request->>'side_code',''),
                    coalesce(oos_request->'frozen_profile'->>'candidate_code','')
                  ORDER BY created_at DESC,admission_id DESC) position
                FROM analytics.trade_outcome_oos_admission_v1
                WHERE status_code='WAITING_FRESH_DATA'
              ) UPDATE analytics.trade_outcome_oos_admission_v1 a
                SET status_code='CLOSED',reason_code='SUPERSEDED_WAITING_ADMISSION'
              FROM ranked r WHERE a.admission_id=r.admission_id AND r.position>1""")
            deduplicated = cursor.rowcount
            cursor.execute("""UPDATE analytics.trade_outcome_oos_admission_v1
                SET status_code='CLOSED',reason_code='WAITING_FRESH_DATA_EXPIRED'
                WHERE status_code='WAITING_FRESH_DATA'
                  AND created_at < clock_timestamp() -
                    (%s * interval '1 day')""",
                (max(7, int(os.getenv("ENTRY_EXIT_OOS_WAITING_TTL_DAYS", "14"))),))
            expired = cursor.rowcount
    print(f"admissions_deduplicated={deduplicated}")
    print(f"admissions_expired={expired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
