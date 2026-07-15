from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from marketcore.presentation.render_tree.v2 import ActionKindV2, RenderActionV2


class InteractionKindV2(str, Enum):
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"


class ActionActorKindV2(str, Enum):
    OPERATOR = "OPERATOR"
    AI = "AI"
    SYSTEM = "SYSTEM"


class ActionContractErrorV2(ValueError):
    pass


_DIRECT_EXECUTION_COMMANDS = frozenset(
    {
        "BROKER.SUBMIT_ORDER",
        "BROKER.CANCEL_ORDER",
        "EXECUTION.PLACE_ORDER",
        "EXECUTION.REPLACE_ORDER",
        "LIVE.SUBMIT_ORDER",
    }
)


@dataclass(frozen=True, slots=True)
class ActionIntentV2:
    action_id: str
    action_kind: ActionKindV2
    interaction_kind: InteractionKindV2
    actor_kind: ActionActorKindV2
    actor_id: str
    target_id: str | None = None
    command_code: str | None = None
    policy_class: str | None = None
    authorization_scope: str | None = None
    requires_approval: bool = False
    reversible: bool = False
    rollback_code: str | None = None
    idempotency_key: str | None = None
    enabled: bool = True


def _required(value: str | None, code: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ActionContractErrorV2(code)
    return normalized


def validate_action_intent_v2(intent: ActionIntentV2) -> ActionIntentV2:
    _required(intent.action_id, "ACTION_ID_REQUIRED")
    _required(intent.actor_id, "ACTION_ACTOR_ID_REQUIRED")

    if not intent.enabled:
        raise ActionContractErrorV2(f"ACTION_DISABLED:{intent.action_id}")

    if intent.action_kind is ActionKindV2.NAVIGATE:
        _required(intent.target_id, "NAVIGATION_TARGET_REQUIRED")
        if any((intent.command_code, intent.policy_class, intent.authorization_scope, intent.idempotency_key)):
            raise ActionContractErrorV2("NAVIGATION_COMMAND_FIELDS_FORBIDDEN")
        if intent.requires_approval or intent.reversible or intent.rollback_code:
            raise ActionContractErrorV2("NAVIGATION_GOVERNANCE_FIELDS_FORBIDDEN")
        return intent

    if intent.action_kind not in {ActionKindV2.COMMAND, ActionKindV2.CONFIRM}:
        raise ActionContractErrorV2(f"ACTION_KIND_NOT_EXECUTABLE:{intent.action_kind.value}")

    command_code = _required(intent.command_code, "ACTION_COMMAND_CODE_REQUIRED").upper()
    _required(intent.policy_class, "ACTION_POLICY_CLASS_REQUIRED")
    _required(intent.authorization_scope, "ACTION_AUTHORIZATION_SCOPE_REQUIRED")
    _required(intent.idempotency_key, "ACTION_IDEMPOTENCY_KEY_REQUIRED")

    if command_code in _DIRECT_EXECUTION_COMMANDS and intent.actor_kind in {
        ActionActorKindV2.OPERATOR,
        ActionActorKindV2.AI,
    }:
        raise ActionContractErrorV2(f"DIRECT_EXECUTION_FORBIDDEN:{command_code}")

    if intent.reversible:
        _required(intent.rollback_code, "ACTION_ROLLBACK_CODE_REQUIRED")
    elif intent.rollback_code is not None:
        raise ActionContractErrorV2("ACTION_ROLLBACK_WITHOUT_REVERSIBILITY")
    elif not intent.requires_approval:
        raise ActionContractErrorV2("IRREVERSIBLE_ACTION_APPROVAL_REQUIRED")

    if intent.action_kind is ActionKindV2.CONFIRM and not intent.requires_approval:
        raise ActionContractErrorV2("CONFIRM_ACTION_APPROVAL_REQUIRED")
    return intent


def action_intent_from_render_action_v2(
    action: RenderActionV2,
    *,
    interaction_kind: InteractionKindV2,
    actor_kind: ActionActorKindV2,
    actor_id: str,
    authorization_scope: str | None = None,
) -> ActionIntentV2:
    intent = ActionIntentV2(
        action_id=action.action_id,
        action_kind=action.action_kind,
        interaction_kind=interaction_kind,
        actor_kind=actor_kind,
        actor_id=actor_id,
        target_id=action.target_id,
        command_code=action.command_code,
        policy_class=action.policy_class,
        authorization_scope=authorization_scope,
        requires_approval=action.requires_approval,
        reversible=action.reversible,
        rollback_code=action.rollback_code,
        idempotency_key=action.idempotency_key,
        enabled=action.enabled,
    )
    return validate_action_intent_v2(intent)
