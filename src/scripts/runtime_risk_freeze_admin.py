from __future__ import annotations

import argparse
import os

import psycopg2


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--action",
        choices=["status", "clear"],
        required=True,
    )

    parser.add_argument(
        "--reason",
        default="manual_clear_after_review",
    )

    args = parser.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

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

            if args.action == "status":
                cur.execute("""
                    select
                        id,
                        created_at,
                        is_active,
                        reason
                    from runtime_risk_freeze
                    order by id desc
                    limit 20
                """)

                rows = cur.fetchall()

                if not rows:
                    print("RUNTIME_RISK_FREEZE_STATUS empty", flush=True)
                    return 0

                for row in rows:
                    print(
                        "RUNTIME_RISK_FREEZE_STATUS "
                        f"id={row[0]} "
                        f"created_at={row[1]} "
                        f"active={row[2]} "
                        f"reason={row[3]}",
                        flush=True,
                    )

                return 0

            if args.action == "clear":
                cur.execute("""
                    update runtime_risk_freeze
                    set
                        is_active = false,
                        raw_json = coalesce(raw_json, '{}'::jsonb)
                            || jsonb_build_object(
                                'cleared_by', 'runtime_risk_freeze_admin',
                                'clear_reason', %s
                            )
                    where is_active = true
                """, (args.reason,))

                print(
                    f"RUNTIME_RISK_FREEZE_CLEARED rows={cur.rowcount} reason={args.reason}",
                    flush=True,
                )

                return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
