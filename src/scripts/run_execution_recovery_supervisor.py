from __future__ import annotations

import os
import subprocess
import sys

import psycopg2


def run_step(name: str, cmd: list[str]) -> None:
    print(f"EXECUTION_RECOVERY_STEP_BEGIN name={name}", flush=True)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(
            f"EXECUTION_RECOVERY_STEP_FAILED name={name} rc={result.returncode}"
        )

    print(f"EXECUTION_RECOVERY_STEP_OK name={name}", flush=True)


def print_oms_health(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            select intent_state, count(*)
            from execution_intents
            group by intent_state
            order by intent_state
        """)

        rows = cur.fetchall()

        for state, cnt in rows:
            print(
                f"OMS_HEALTH_STATE state={state} count={cnt}",
                flush=True,
            )

        cur.execute("""
            select count(*)
            from execution_intents
            where intent_state in (
                'ACK',
                'SENT',
                'SENDING',
                'RECONCILE_REQUIRED'
            )
        """)

        unresolved = int(cur.fetchone()[0] or 0)

        print(
            f"OMS_HEALTH_UNRESOLVED unresolved={unresolved}",
            flush=True,
        )


def stale_watchdog(conn) -> None:
    stale_sec = int(
        os.getenv(
            "EXECUTION_STALE_ACK_THRESHOLD_SEC",
            "300",
        )
    )

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                update execution_intents
                set
                    intent_state = 'RECONCILE_REQUIRED',
                    updated_at = now(),
                    reason = 'stale_ack_watchdog'
                where intent_state in ('ACK', 'SENT', 'SENDING')
                  and updated_at < now() - (%s || ' seconds')::interval
                returning id, symbol, side
            """, (stale_sec,))

            rows = cur.fetchall()

            for intent_id, symbol, side in rows:
                print(
                    "EXECUTION_STALE_WATCHDOG_RECONCILE "
                    f"intent_id={intent_id} "
                    f"symbol={symbol} side={side}",
                    flush=True,
                )

        print(
            f"EXECUTION_STALE_WATCHDOG_OK recovered={len(rows)}",
            flush=True,
        )


def main() -> int:
    dsn = os.getenv("DATABASE_URL")

    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    python = sys.executable

    run_step(
        "sending_intent_recovery",
        [
            python,
            "src/scripts/run_sending_intent_recovery.py",
        ],
    )

    run_step(
        "real_order_state_sync",
        [
            python,
            "src/scripts/run_real_order_state_synchronizer.py",
        ],
    )

    conn = psycopg2.connect(dsn)

    stale_watchdog(conn)

    print_oms_health(conn)

    print(
        "EXECUTION_RECOVERY_SUPERVISOR_OK",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
