from __future__ import annotations

import json
import os
import psycopg2

from finam_core.execution.execution_lifecycle_determinism import (
    ExecutionLifecycleDeterminism,
)


def main() -> int:

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    violations = 0

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
                create table if not exists execution_state_transitions (
                    id bigserial primary key,
                    created_at timestamptz not null default now(),
                    intent_id bigint not null,
                    previous_state text not null,
                    next_state text not null
                )
            """)

            cur.execute("""
                select
                    id,
                    intent_id,
                    previous_state,
                    next_state
                from execution_state_transitions
                order by id asc
            """)

            rows = cur.fetchall()

            validator = ExecutionLifecycleDeterminism()

            for row in rows:

                transition_id = int(row[0])
                intent_id = int(row[1])
                previous_state = str(row[2] or "")
                next_state = str(row[3] or "")

                decision = validator.validate_transition(
                    previous_state=previous_state,
                    next_state=next_state,
                )

                if not decision.allowed:

                    violations += 1

                    print(
                        "EXECUTION_LIFECYCLE_VIOLATION "
                        f"transition_id={transition_id} "
                        f"intent_id={intent_id} "
                        f"reason={decision.reason}",
                        flush=True,
                    )

            if violations > 0:

                cur.execute("""
                    create table if not exists runtime_risk_freeze (
                        id bigserial primary key,
                        created_at timestamptz not null default now(),
                        is_active boolean not null default true,
                        reason text not null,
                        raw_json jsonb not null default '{}'::jsonb
                    )
                """)

                cur.execute("""
                    insert into runtime_risk_freeze (
                        is_active,
                        reason,
                        raw_json
                    )
                    values (
                        true,
                        %s,
                        %s::jsonb
                    )
                """, (
                    "execution_lifecycle_determinism_violation",
                    json.dumps({
                        "violations": violations,
                    }),
                ))

                print(
                    f"EXECUTION_LIFECYCLE_RUNTIME_FREEZE violations={violations}",
                    flush=True,
                )

                return 1

    print(
        f"EXECUTION_LIFECYCLE_DETERMINISM_OK violations={violations}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
