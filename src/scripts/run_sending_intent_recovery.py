from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    threshold_sec = int(os.getenv("SENDING_INTENT_RECOVERY_THRESHOLD_SEC", "30"))

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update execution_intents
                set
                    intent_state = 'RECONCILE_REQUIRED',
                    reason = 'sending_intent_recovery:broker_state_unknown',
                    updated_at = now()
                where intent_state = 'SENDING'
                  and updated_at < now() - (%s || ' seconds')::interval
                returning id, symbol, side, planned_qty
                """,
                (threshold_sec,),
            )

            rows = cur.fetchall()

            for intent_id, symbol, side, qty in rows:
                print(
                    "SENDING_INTENT_RECOVERY_RECONCILE_REQUIRED "
                    f"intent_id={intent_id} symbol={symbol} side={side} qty={qty}",
                    flush=True,
                )

    print(
        f"SENDING_INTENT_RECOVERY_OK recovered={len(rows)} threshold_sec={threshold_sec}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
