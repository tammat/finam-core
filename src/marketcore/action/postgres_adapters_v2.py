from __future__ import annotations

from datetime import datetime
from typing import Callable, Protocol

import psycopg2

from marketcore.action.dispatcher_v2 import ActionAuditEventV2


class DbConnectionV2(Protocol):
    def __enter__(self): ...
    def __exit__(self, exc_type, exc, traceback): ...
    def cursor(self): ...


ConnectionFactoryV2 = Callable[[], DbConnectionV2]


def default_action_connection_v2() -> DbConnectionV2:
    return psycopg2.connect("postgresql:///finam_core")


class PostgresActionAuditTrailV2:
    def __init__(self, connection_factory: ConnectionFactoryV2 = default_action_connection_v2) -> None:
        self._connection_factory = connection_factory

    def append(self, event: ActionAuditEventV2) -> None:
        if event.occurred_at.tzinfo is None:
            raise ValueError("ACTION_AUDIT_TIMESTAMP_NOT_TIMEZONE_AWARE")
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO marketcore_action.action_audit_v2 (
                        occurred_at,stage,action_id,actor_id,interaction_kind,status,
                        reason_code,target_id,command_code,policy_class,risk_guard_code,
                        idempotency_key,approval_granted,result_reference
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        event.occurred_at,
                        event.stage.value,
                        event.action_id,
                        event.actor_id,
                        event.interaction_kind,
                        event.status.value,
                        event.reason_code,
                        event.target_id,
                        event.command_code,
                        event.policy_class,
                        event.risk_guard_code,
                        event.idempotency_key,
                        event.approval_granted,
                        event.result_reference,
                    ),
                )


class PostgresDuplicateActionGuardV2:
    def __init__(self, connection_factory: ConnectionFactoryV2 = default_action_connection_v2) -> None:
        self._connection_factory = connection_factory

    def claim(self, idempotency_key: str, *, now: datetime) -> bool:
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
        if now.tzinfo is None:
            raise ValueError("IDEMPOTENCY_TIMESTAMP_NOT_TIMEZONE_AWARE")
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO marketcore_action.idempotency_claim_v2 (
                        idempotency_key,claimed_at
                    ) VALUES (%s,%s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING idempotency_key
                    """,
                    (normalized_key, now),
                )
                return cursor.fetchone() is not None
