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

    send_ok = os.getenv("RELIABILITY_GUARD_SEND_OK", "0") == "1"

    issues: list[str] = []

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                create table if not exists runtime_risk_freeze (
                    id bigserial primary key,
                    created_at timestamptz not null default now(),
                    is_active boolean not null default true,
                    reason text not null,
                    raw_json jsonb not null default '{}'::jsonb
                )
            """)

            stale_ready_queue = scalar(cur, """
                select count(*)
                from portfolio_execution_queue
                where queue_state in ('READY','RESERVED')
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

            high_reconciliation = scalar(cur, """
                select count(*)
                from portfolio_reconciliation_events
                where severity = 'HIGH'
                  and coalesce(is_archived, false) = false
                  and created_at >= now() - interval '60 minutes'
            """)

            if stale_ready_queue:
                issues.append(f"stale_queue={stale_ready_queue}")

            if stale_intents:
                issues.append(f"stale_intents={stale_intents}")

            if filled_not_accounted:
                issues.append(f"filled_not_accounted={filled_not_accounted}")

            if high_reconciliation:
                issues.append(f"high_reconciliation={high_reconciliation}")

            if issues:
                reason = "runtime_reliability_guard:" + ";".join(issues)

                cur.execute("""
                    insert into runtime_risk_freeze (
                        is_active,
                        reason,
                        raw_json
                    )
                    values (
                        true,
                        %s,
                        jsonb_build_object(
                            'issues', %s,
                            'guard', 'runtime_reliability_guard_v1'
                        )
                    )
                """, (reason, issues))

                text = (
                    "🛑 Runtime Reliability Guard\n\n"
                    "Статус: CRITICAL\n"
                    "Новые реальные BUY должны быть заблокированы.\n\n"
                    "Проблемы:\n"
                    + "\n".join(f"• {x}" for x in issues)
                )

                TelegramNotifier().send(text)

                print(
                    f"RUNTIME_RELIABILITY_GUARD_CRITICAL issues={len(issues)} freeze=1",
                    flush=True,
                )

                return 1

    if send_ok:
        TelegramNotifier().send(
            "✅ Runtime Reliability Guard\n\nСтатус: OK. Критических runtime-проблем нет."
        )

    print("RUNTIME_RELIABILITY_GUARD_OK issues=0 freeze=0", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
