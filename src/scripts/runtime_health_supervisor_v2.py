from __future__ import annotations

import os
import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    row = cur.fetchone()
    return int(row[0] or 0)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    send_ok = os.getenv("RUNTIME_HEALTH_V2_SEND_OK", "0") == "1"

    conn = psycopg2.connect(dsn)

    issues: list[str] = []

    with conn:
        with conn.cursor() as cur:
            stale_ready_queue = scalar(cur, """
                select count(*)
                from portfolio_execution_queue
                where queue_state = 'READY'
                  and updated_at < now() - interval '30 minutes'
            """)

            stale_reserved_queue = scalar(cur, """
                select count(*)
                from portfolio_execution_queue
                where queue_state = 'RESERVED'
                  and updated_at < now() - interval '30 minutes'
            """)

            stale_intents = scalar(cur, """
                select count(*)
                from execution_intents
                where intent_state in ('READY','RESERVED','SENT','ACK','PARTIAL_FILL')
                  and updated_at < now() - interval '30 minutes'
            """)

            filled_not_accounted = scalar(cur, """
                select count(*)
                from execution_intents
                where intent_state = 'FILLED'
                  and coalesce(raw_json->>'accounted','false') != 'true'
            """)

            orphan_lifecycle = scalar(cur, """
                select count(*)
                from position_lifecycle_state l
                where coalesce(l.remaining_qty, 0) > 0
                  and not exists (
                      select 1
                      from real_portfolio_positions p
                      where p.symbol = l.symbol
                        and coalesce(p.qty, 0) > 0
                  )
            """)

            orphan_positions = scalar(cur, """
                select count(*)
                from real_portfolio_positions p
                where coalesce(p.qty, 0) > 0
                  and not exists (
                      select 1
                      from position_lifecycle_state l
                      where l.symbol = p.symbol
                        and coalesce(l.remaining_qty, 0) > 0
                  )
            """)

            high_reconciliation_issues = scalar(cur, """
                select count(*)
                from portfolio_reconciliation_events
                where severity = 'HIGH'
                  and coalesce(is_archived, false) = false
                  and created_at >= now() - interval '60 minutes'
            """)

            active_signals_without_monitoring = scalar(cur, """
                select count(*)
                from signal_lifecycle
                where state in ('NEW','ACTIVE','TRIGGERED')
                  and created_at < now() - interval '60 minutes'
            """)

    if stale_ready_queue:
        issues.append(f"stale READY queue: {stale_ready_queue}")

    if stale_reserved_queue:
        issues.append(f"stale RESERVED queue: {stale_reserved_queue}")

    if stale_intents:
        issues.append(f"stale execution intents: {stale_intents}")

    if filled_not_accounted:
        issues.append(f"FILLED not accounted: {filled_not_accounted}")

    if orphan_lifecycle:
        issues.append(f"orphan lifecycle: {orphan_lifecycle}")

    if orphan_positions:
        issues.append(f"orphan positions: {orphan_positions}")

    if high_reconciliation_issues:
        issues.append(f"HIGH reconciliation issues 60m: {high_reconciliation_issues}")

    if active_signals_without_monitoring:
        issues.append(f"stale signal lifecycle: {active_signals_without_monitoring}")

    status = "CRITICAL" if issues else "OK"

    print(
        "RUNTIME_HEALTH_SUPERVISOR_V2_OK "
        f"status={status} "
        f"issues={len(issues)}",
        flush=True,
    )

    if issues or send_ok:
        text = (
            "🧭 Runtime Health Supervisor v2\n\n"
            f"Статус: {status}\n\n"
        )

        if issues:
            text += "Проблемы:\n" + "\n".join(f"• {x}" for x in issues)
        else:
            text += "Очередь, intents, lifecycle и reconciliation в норме."

        TelegramNotifier().send(text)

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
