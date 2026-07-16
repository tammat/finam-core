from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from marketcore.action.authorization_v2 import AuthorizationGrantV2, ScopeAuthorizationEngineV2
from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.action.dispatcher_v2 import GovernedActionDispatcherV2
from marketcore.action.policy_v2 import ActionPolicyContextV2, ActionPolicyRuleV2, AutonomyModeV2, StaticActionPolicyEngineV2
from marketcore.action.handler_registry_v2 import PostgresCommandRequestHandlerV2, resolve_state_changing_action_v2
from marketcore.action.postgres_adapters_v2 import PostgresActionAuditTrailV2, PostgresDuplicateActionGuardV2
from marketcore.action.postgres_risk_boundary_v2 import PostgresRiskBoundaryV2
from marketcore.presentation.navigation.container_registry_v2 import resolve_container_v2
from marketcore.presentation.render_tree.v2 import ActionKindV2


@dataclass(frozen=True, slots=True)
class ActionHttpResponseV2:
    status_code: int
    body: bytes


def _response(http_status: int, **payload: object) -> ActionHttpResponseV2:
    return ActionHttpResponseV2(http_status, json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def dispatch_browser_action_http_v2(body: bytes) -> ActionHttpResponseV2:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _response(400, status="DENIED", reason_code="ACTION_JSON_INVALID")
    if not isinstance(payload, dict):
        return _response(400, status="DENIED", reason_code="ACTION_OBJECT_REQUIRED")
    action_kind = payload.get("actionKind")
    if action_kind not in {"NAVIGATE", "COMMAND"}:
        return _response(403, status="DENIED", reason_code="STATE_CHANGING_ACTION_NOT_REGISTERED")
    try:
        interaction = InteractionKindV2(str(payload.get("interactionKind")))
        action_id = str(payload.get("actionId") or "").strip()
        target_id = str(payload.get("targetId") or "").strip() or None
    except ValueError:
        return _response(400, status="DENIED", reason_code="ACTION_INTERACTION_INVALID")

    actor_id = os.getenv("MARKETCORE_OPERATOR_ID", "operator.local")
    if action_kind == "NAVIGATE":
        try:
            resolve_container_v2(str(target_id))
            if not action_id or not (action_id.startswith("navigation.") or action_id.startswith("home.navigate.")):
                raise ValueError("ACTION_ID_INVALID")
        except ValueError:
            return _response(400, status="DENIED", reason_code="NAVIGATION_ACTION_INVALID")
        intent = ActionIntentV2(action_id, ActionKindV2.NAVIGATE, interaction, ActionActorKindV2.OPERATOR, actor_id, target_id=target_id)
        grant = None
        rules = {}
        autonomy_mode = AutonomyModeV2.ADVISORY
    else:
        try:
            definition = resolve_state_changing_action_v2(action_id)
            request_id = str(UUID(str(payload.get("requestId"))))
            command_target_id = str(payload.get("targetId") or "").strip() or None
            if definition.request_kind == "OPERATOR_DECISION_ACKNOWLEDGE":
                command_target_id = str(UUID(str(command_target_id)))
            if interaction is not InteractionKindV2.DOUBLE_CLICK:
                raise ValueError("DOUBLE_CLICK_REQUIRED")
        except ValueError:
            return _response(403, status="DENIED", reason_code="STATE_CHANGING_ACTION_NOT_REGISTERED")
        intent = ActionIntentV2(
            action_id, ActionKindV2.COMMAND, interaction, ActionActorKindV2.OPERATOR, actor_id,
            target_id=command_target_id,
            command_code=definition.command_code, policy_class=definition.policy_class,
            authorization_scope=definition.authorization_scope, reversible=True,
            rollback_code=definition.rollback_code, idempotency_key=request_id,
        )
        grant = AuthorizationGrantV2(actor_id, frozenset({definition.authorization_scope}))
        rules = {definition.policy_class: ActionPolicyRuleV2(
            definition.policy_class, frozenset({AutonomyModeV2.RECOMMEND}),
            frozenset({ActionActorKindV2.OPERATOR}), rollback_allowed=True,
        )}
        autonomy_mode = AutonomyModeV2.RECOMMEND
    dispatcher = GovernedActionDispatcherV2(
        authorization=ScopeAuthorizationEngineV2(),
        policy=StaticActionPolicyEngineV2(rules),
        risk=PostgresRiskBoundaryV2(),
        duplicate_guard=PostgresDuplicateActionGuardV2(),
        audit_trail=PostgresActionAuditTrailV2(),
        command_handler=PostgresCommandRequestHandlerV2(),
    )
    result = dispatcher.dispatch(
        intent,
        grant=grant,
        policy_context=ActionPolicyContextV2(autonomy_mode, datetime.now(timezone.utc)),
    )
    request_accepted = result.status.value == "EXECUTED" and action_kind == "COMMAND"
    return _response(
        (202 if result.status.value == "EXECUTED" else 200) if result.successful else 403,
        status="ACCEPTED" if request_accepted else result.status.value,
        reason_code="COMMAND_REQUEST_ACCEPTED" if request_accepted else result.reason_code,
        action_id=result.action_id,
        target_id=result.target_id,
        result_reference=result.result_reference,
        request_status="PENDING" if request_accepted else None,
    )
