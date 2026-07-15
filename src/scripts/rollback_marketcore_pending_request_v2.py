from __future__ import annotations

import argparse
from datetime import datetime, timezone

import psycopg2

from marketcore.action.authorization_v2 import AuthorizationGrantV2, ScopeAuthorizationEngineV2
from marketcore.action.command_worker_v2 import PostgresPendingRequestRollbackHandlerV2
from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.action.handler_registry_v2 import resolve_state_changing_action_v2
from marketcore.action.policy_v2 import ActionPolicyContextV2, ActionPolicyRuleV2, AutonomyModeV2, StaticActionPolicyEngineV2
from marketcore.action.postgres_adapters_v2 import PostgresActionAuditTrailV2, PostgresDuplicateActionGuardV2
from marketcore.action.rollback_v2 import GovernedRollbackCoordinatorV2, RollbackRequestV2
from marketcore.presentation.render_tree.v2 import ActionKindV2


def main() -> int:
    parser = argparse.ArgumentParser(description="Cancel one governed command request while it is still pending")
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--actor-id", default="operator.local")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT action_id,command_code FROM marketcore_action.command_request_v2 WHERE request_id=%s",
                (args.request_id,),
            )
            row = cursor.fetchone()
    if row is None:
        parser.error("request not found")
    definition = resolve_state_changing_action_v2(row[0])
    if row[1] != definition.command_code:
        parser.error("request command does not match the registry")

    intent = ActionIntentV2(
        action_id=definition.action_id,
        action_kind=ActionKindV2.COMMAND,
        interaction_kind=InteractionKindV2.DOUBLE_CLICK,
        actor_kind=ActionActorKindV2.OPERATOR,
        actor_id=args.actor_id,
        command_code=definition.command_code,
        policy_class=definition.policy_class,
        authorization_scope=definition.authorization_scope,
        reversible=True,
        rollback_code=definition.rollback_code,
        idempotency_key=args.request_id,
    )
    rule = ActionPolicyRuleV2(
        definition.policy_class,
        frozenset({AutonomyModeV2.RECOMMEND}),
        frozenset({ActionActorKindV2.OPERATOR}),
        rollback_allowed=True,
    )
    coordinator = GovernedRollbackCoordinatorV2(
        authorization=ScopeAuthorizationEngineV2(),
        policy=StaticActionPolicyEngineV2({definition.policy_class: rule}),
        duplicate_guard=PostgresDuplicateActionGuardV2(),
        audit_trail=PostgresActionAuditTrailV2(),
        rollback_handler=PostgresPendingRequestRollbackHandlerV2(),
    )
    result = coordinator.rollback(
        RollbackRequestV2(intent, args.request_id),
        grant=AuthorizationGrantV2(args.actor_id, frozenset({definition.authorization_scope})),
        policy_context=ActionPolicyContextV2(
            AutonomyModeV2.RECOMMEND,
            datetime.now(timezone.utc),
            approval_granted=args.approve,
        ),
    )
    print(f"status={result.status.value}")
    print(f"reason_code={result.reason_code}")
    print(f"result_reference={result.result_reference or ''}")
    return 0 if result.successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
