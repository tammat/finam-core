from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from marketcore.action.authorization_v2 import ScopeAuthorizationEngineV2
from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.action.dispatcher_v2 import GovernedActionDispatcherV2
from marketcore.action.policy_v2 import ActionPolicyContextV2, AutonomyModeV2, StaticActionPolicyEngineV2
from marketcore.action.postgres_adapters_v2 import PostgresActionAuditTrailV2, PostgresDuplicateActionGuardV2
from marketcore.action.postgres_risk_boundary_v2 import PostgresRiskBoundaryV2
from marketcore.presentation.navigation.container_registry_v2 import resolve_container_v2
from marketcore.presentation.render_tree.v2 import ActionKindV2


@dataclass(frozen=True, slots=True)
class ActionHttpResponseV2:
    status_code: int
    body: bytes


class _NoStateChangingHandlerV2:
    def execute(self, intent: ActionIntentV2) -> str:
        raise RuntimeError(f"STATE_CHANGING_ACTION_NOT_REGISTERED:{intent.action_id}")


def _response(http_status: int, **payload: object) -> ActionHttpResponseV2:
    return ActionHttpResponseV2(http_status, json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def dispatch_browser_action_http_v2(body: bytes) -> ActionHttpResponseV2:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _response(400, status="DENIED", reason_code="ACTION_JSON_INVALID")
    if not isinstance(payload, dict):
        return _response(400, status="DENIED", reason_code="ACTION_OBJECT_REQUIRED")
    if payload.get("actionKind") != "NAVIGATE":
        return _response(403, status="DENIED", reason_code="STATE_CHANGING_ACTION_NOT_REGISTERED")
    try:
        interaction = InteractionKindV2(str(payload.get("interactionKind")))
        action_id = str(payload.get("actionId") or "").strip()
        target_id = str(payload.get("targetId") or "").strip()
        resolve_container_v2(target_id)
        if not action_id or not (action_id.startswith("navigation.") or action_id.startswith("home.navigate.")):
            raise ValueError("ACTION_ID_INVALID")
    except ValueError:
        return _response(400, status="DENIED", reason_code="NAVIGATION_ACTION_INVALID")

    actor_id = os.getenv("MARKETCORE_OPERATOR_ID", "operator.local-readonly")
    intent = ActionIntentV2(
        action_id=action_id,
        action_kind=ActionKindV2.NAVIGATE,
        interaction_kind=interaction,
        actor_kind=ActionActorKindV2.OPERATOR,
        actor_id=actor_id,
        target_id=target_id,
    )
    dispatcher = GovernedActionDispatcherV2(
        authorization=ScopeAuthorizationEngineV2(),
        policy=StaticActionPolicyEngineV2({}),
        risk=PostgresRiskBoundaryV2(),
        duplicate_guard=PostgresDuplicateActionGuardV2(),
        audit_trail=PostgresActionAuditTrailV2(),
        command_handler=_NoStateChangingHandlerV2(),
    )
    result = dispatcher.dispatch(
        intent,
        grant=None,
        policy_context=ActionPolicyContextV2(AutonomyModeV2.ADVISORY, datetime.now(timezone.utc)),
    )
    return _response(
        200 if result.successful else 403,
        status=result.status.value,
        reason_code=result.reason_code,
        action_id=result.action_id,
        target_id=result.target_id,
    )
