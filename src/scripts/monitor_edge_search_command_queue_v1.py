from __future__ import annotations

import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
RESOURCE_GUARD_RETRY_COOLDOWN_SECONDS = int(
    os.getenv("EDGE_SEARCH_RESOURCE_GUARD_RETRY_COOLDOWN_SECONDS", "600")
)

RESOURCE_GUARD_RESULT = "VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK"
RESOURCE_GUARD_RETRY_REASON = "AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK"

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def heavy_search_window_open(now: datetime | None = None) -> bool:
    current = now or datetime.now(MOSCOW_TZ)
    return current.weekday() >= 5 or current.hour < 9


def main() -> int:
    if RESOURCE_GUARD_RETRY_COOLDOWN_SECONDS < 60:
        raise RuntimeError("RESOURCE_GUARD_RETRY_COOLDOWN_TOO_SMALL")

    with psycopg2.connect(DB) as connection:
        with connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cursor:
            # 1. Восстановление действительно зависших RUNNING requests.
            cursor.execute(
                """
                UPDATE marketcore_action.command_request_v2
                SET
                    status='FAILED',
                    finished_at=clock_timestamp(),
                    failure_code='EDGE_SEARCH_RUNNING_TIMEOUT'
                WHERE request_kind='EDGE_SEARCH_RUN'
                  AND status='RUNNING'
                  AND started_at < clock_timestamp() - interval '2 hours'
                """
            )
            running_recovered = cursor.rowcount

            # 2. Просроченные PENDING requests.
            cursor.execute(
                """
                UPDATE marketcore_action.command_request_v2
                SET
                    status='FAILED',
                    finished_at=clock_timestamp(),
                    failure_code='EDGE_SEARCH_PENDING_EXPIRED'
                WHERE request_kind='EDGE_SEARCH_RUN'
                  AND status='PENDING'
                  AND requested_at < clock_timestamp() - interval '24 hours'
                """
            )
            pending_expired = cursor.rowcount

            # 3. Существующий technical retry.
            cursor.execute(
                """
                SELECT q.*
                FROM marketcore_action.command_request_v2 q
                LEFT JOIN marketcore_action.edge_search_retry_v1 r
                  ON r.source_request_id=q.request_id
                WHERE q.request_kind='EDGE_SEARCH_RUN'
                  AND q.status='FAILED'
                  AND r.source_request_id IS NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM marketcore_action.edge_search_retry_v1 parent_retry
                      WHERE parent_retry.retry_request_id=q.request_id
                  )
                  AND q.failure_code LIKE 'WORKER_COMMAND_FAILED:%'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM marketcore_action.command_request_v2
                      WHERE request_kind='EDGE_SEARCH_RUN'
                        AND status IN ('PENDING','RUNNING')
                  )
                ORDER BY q.finished_at DESC
                LIMIT 1
                """
            )
            failed = cursor.fetchone()
            technical_retry_created = 0

            if failed:
                retry_id = str(uuid.uuid4())

                cursor.execute(
                    """
                    INSERT INTO marketcore_action.command_request_v2
                    (
                        request_id,
                        action_id,
                        request_kind,
                        command_code,
                        actor_id,
                        target_id,
                        status,
                        requested_at,
                        process_id
                    )
                    VALUES
                    (
                        %s,%s,'EDGE_SEARCH_RUN','RESEARCH.RUN_EDGE_SEARCH',
                        %s,%s,'PENDING',clock_timestamp(),%s
                    )
                    """,
                    (
                        retry_id,
                        failed["action_id"],
                        failed["actor_id"],
                        failed["target_id"],
                        failed["process_id"],
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO marketcore_action.edge_search_retry_v1
                    (
                        source_request_id,
                        retry_request_id,
                        retry_reason,
                        created_at
                    )
                    VALUES (%s,%s,%s,clock_timestamp())
                    """,
                    (
                        failed["request_id"],
                        retry_id,
                        failed["failure_code"],
                    ),
                )
                technical_retry_created = 1

            # 4. Deferred retry после RESOURCE_GUARD_OK.
            #
            # В отличие от checkpoint continuation:
            # - retry НЕ создаётся самим worker;
            # - ждём cooldown;
            # - активный EDGE_SEARCH_RUN блокирует создание;
            # - source_request_id PK обеспечивает один retry на source.
            cursor.execute(
                """
                SELECT q.*
                FROM marketcore_action.command_request_v2 q
                LEFT JOIN marketcore_action.edge_search_retry_v1 r
                  ON r.source_request_id=q.request_id
                WHERE q.request_kind='EDGE_SEARCH_RUN'
                  AND q.status='COMPLETED'
                  AND q.result_reference=%s
                  AND r.source_request_id IS NULL
                  AND q.finished_at IS NOT NULL
                  AND q.finished_at
                      <= clock_timestamp()
                         - (%s * interval '1 second')
                  AND NOT EXISTS (
                      SELECT 1
                      FROM marketcore_action.command_request_v2 active
                      WHERE active.request_kind='EDGE_SEARCH_RUN'
                        AND active.status IN ('PENDING','RUNNING')
                  )
                ORDER BY q.finished_at DESC
                LIMIT 1
                """,
                (
                    RESOURCE_GUARD_RESULT,
                    RESOURCE_GUARD_RETRY_COOLDOWN_SECONDS,
                ),
            )
            deferred = cursor.fetchone()
            resource_guard_retry_created = 0
            resource_guard_retry_window_open = heavy_search_window_open()

            if deferred and resource_guard_retry_window_open:
                retry_id = str(
                    uuid.uuid5(
                        uuid.UUID(str(deferred["request_id"])),
                        "EDGE_SEARCH_RESOURCE_GUARD_DEFERRED_RETRY_V1",
                    )
                )

                cursor.execute(
                    """
                    INSERT INTO marketcore_action.command_request_v2
                    (
                        request_id,
                        action_id,
                        request_kind,
                        command_code,
                        actor_id,
                        target_id,
                        status,
                        requested_at,
                        process_id
                    )
                    VALUES
                    (
                        %s,%s,'EDGE_SEARCH_RUN',%s,
                        %s,%s,'PENDING',clock_timestamp(),%s
                    )
                    ON CONFLICT(request_id) DO NOTHING
                    """,
                    (
                        retry_id,
                        deferred["action_id"],
                        deferred["command_code"],
                        deferred["actor_id"],
                        deferred["target_id"],
                        deferred["process_id"],
                    ),
                )
                request_inserted = cursor.rowcount

                if request_inserted:
                    cursor.execute(
                        """
                        INSERT INTO marketcore_action.edge_search_retry_v1
                        (
                            source_request_id,
                            retry_request_id,
                            retry_reason,
                            created_at
                        )
                        VALUES (%s,%s,%s,clock_timestamp())
                        ON CONFLICT(source_request_id) DO NOTHING
                        """,
                        (
                            deferred["request_id"],
                            retry_id,
                            RESOURCE_GUARD_RETRY_REASON,
                        ),
                    )
                    resource_guard_retry_created = 1

    print(f"running_recovered={running_recovered}")
    print(f"pending_expired={pending_expired}")
    print(f"technical_retry_created={technical_retry_created}")
    print(
        "resource_guard_retry_cooldown_seconds="
        f"{RESOURCE_GUARD_RETRY_COOLDOWN_SECONDS}"
    )
    print(
        f"resource_guard_retry_created={resource_guard_retry_created}"
    )
    print(
        f"resource_guard_retry_window_open={int(resource_guard_retry_window_open)}"
    )
    print("resource_guard_immediate_retry=0")
    print("VERDICT=EDGE_SEARCH_QUEUE_MONITOR_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
