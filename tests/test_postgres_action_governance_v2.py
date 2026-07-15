from datetime import datetime, timezone
from uuid import uuid4

import psycopg2
import pytest

from marketcore.action.dispatcher_v2 import ActionAuditEventV2, AuditStageV2, DispatchStatusV2
from marketcore.action.postgres_adapters_v2 import PostgresActionAuditTrailV2, PostgresDuplicateActionGuardV2


DSN = "postgresql:///finam_core"


def test_postgres_idempotency_claim_is_atomic() -> None:
    key = f"stage5-test-{uuid4()}"
    guard = PostgresDuplicateActionGuardV2()
    now = datetime.now(timezone.utc)
    assert guard.claim(key, now=now) is True
    assert guard.claim(key, now=now) is False
    with psycopg2.connect(DSN) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM marketcore_action.idempotency_claim_v2 WHERE idempotency_key=%s", (key,))


def test_postgres_audit_is_persisted_and_immutable() -> None:
    action_id = f"stage5.audit.test.{uuid4()}"
    PostgresActionAuditTrailV2().append(
        ActionAuditEventV2(
            occurred_at=datetime.now(timezone.utc),
            stage=AuditStageV2.DECISION,
            action_id=action_id,
            actor_id="test.stage5",
            interaction_kind="DOUBLE_CLICK",
            status=DispatchStatusV2.DENIED,
            reason_code="INTEGRATION_TEST",
            target_id=None,
            command_code="TEST.NOOP",
            policy_class="TEST",
            risk_guard_code=None,
            idempotency_key=None,
            approval_granted=False,
        )
    )
    with psycopg2.connect(DSN) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT audit_id,status FROM marketcore_action.action_audit_v2 WHERE action_id=%s", (action_id,))
            audit_id, status = cursor.fetchone()
            assert status == "DENIED"
            with pytest.raises(psycopg2.Error, match="ACTION_AUDIT_V2_APPEND_ONLY"):
                cursor.execute("UPDATE marketcore_action.action_audit_v2 SET reason_code='MUTATED' WHERE audit_id=%s", (audit_id,))
