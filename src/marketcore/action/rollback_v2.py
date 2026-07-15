from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from marketcore.action.authorization_v2 import AuthorizationGrantV2
from marketcore.action.contract_v2 import ActionIntentV2, validate_action_intent_v2
from marketcore.action.dispatcher_v2 import (
    ActionAuditEventV2,
    ActionAuditTrailV2,
    ActionDispatchErrorV2,
    ActionDispatchResultV2,
    AuditStageV2,
    DispatchStatusV2,
    DuplicateActionGuardV2,
)
from marketcore.action.policy_v2 import ActionPolicyContextV2


class RollbackHandlerV2(Protocol):
    def rollback(self, intent: ActionIntentV2, rollback_code: str, result_reference: str) -> str: ...


class AuthorizationBoundaryV2(Protocol):
    def authorize(self, intent: ActionIntentV2, grant: AuthorizationGrantV2 | None, *, now) -> Any: ...


class PolicyBoundaryV2(Protocol):
    def evaluate(self, intent: ActionIntentV2, context: ActionPolicyContextV2) -> Any: ...


@dataclass(frozen=True, slots=True)
class RollbackRequestV2:
    intent: ActionIntentV2
    result_reference: str


class GovernedRollbackCoordinatorV2:
    def __init__(
        self,
        *,
        authorization: AuthorizationBoundaryV2,
        policy: PolicyBoundaryV2,
        duplicate_guard: DuplicateActionGuardV2,
        audit_trail: ActionAuditTrailV2,
        rollback_handler: RollbackHandlerV2,
    ) -> None:
        self._authorization = authorization
        self._policy = policy
        self._duplicate_guard = duplicate_guard
        self._audit_trail = audit_trail
        self._rollback_handler = rollback_handler

    def _audit(self, request: RollbackRequestV2, context: ActionPolicyContextV2, stage: AuditStageV2, status: DispatchStatusV2, reason: str, result: str | None = None) -> None:
        intent = request.intent
        try:
            self._audit_trail.append(ActionAuditEventV2(
                occurred_at=context.now, stage=stage, action_id=intent.action_id,
                actor_id=intent.actor_id, interaction_kind=intent.interaction_kind.value,
                status=status, reason_code=reason, target_id=intent.target_id,
                command_code=intent.rollback_code, policy_class=intent.policy_class,
                risk_guard_code=None, idempotency_key=f"rollback:{intent.idempotency_key}",
                approval_granted=context.approval_granted, result_reference=result,
            ))
        except Exception as exc:
            raise ActionDispatchErrorV2("ROLLBACK_AUDIT_UNAVAILABLE") from exc

    def rollback(self, request: RollbackRequestV2, *, grant: AuthorizationGrantV2 | None, policy_context: ActionPolicyContextV2) -> ActionDispatchResultV2:
        intent = validate_action_intent_v2(request.intent)
        if not intent.reversible or not intent.rollback_code:
            return self._deny(request, policy_context, "ROLLBACK_NOT_DEFINED")
        if not request.result_reference.strip():
            return self._deny(request, policy_context, "ROLLBACK_RESULT_REFERENCE_REQUIRED")

        authorization = self._authorization.authorize(intent, grant, now=policy_context.now)
        if not authorization.allowed:
            return self._deny(request, policy_context, authorization.reason_code)
        policy = self._policy.evaluate(intent, policy_context)
        if not policy.allowed:
            return self._deny(request, policy_context, policy.reason_code)
        if not policy.rollback_allowed:
            return self._deny(request, policy_context, "ROLLBACK_POLICY_FORBIDDEN")
        if policy.rollback_requires_approval and not policy_context.approval_granted:
            self._audit(request, policy_context, AuditStageV2.DECISION, DispatchStatusV2.APPROVAL_REQUIRED, "ROLLBACK_APPROVAL_REQUIRED")
            return ActionDispatchResultV2(DispatchStatusV2.APPROVAL_REQUIRED, "ROLLBACK_APPROVAL_REQUIRED", intent.action_id)

        rollback_key = f"rollback:{intent.idempotency_key}"
        try:
            claimed = self._duplicate_guard.claim(rollback_key, now=policy_context.now)
        except Exception:
            return self._deny(request, policy_context, "ROLLBACK_DUPLICATE_GUARD_UNAVAILABLE")
        if not claimed:
            self._audit(request, policy_context, AuditStageV2.DECISION, DispatchStatusV2.DUPLICATE, "ROLLBACK_DUPLICATE")
            return ActionDispatchResultV2(DispatchStatusV2.DUPLICATE, "ROLLBACK_DUPLICATE", intent.action_id)

        self._audit(request, policy_context, AuditStageV2.ROLLBACK_STARTED, DispatchStatusV2.ROLLED_BACK, "ROLLBACK_AUTHORIZED")
        try:
            result = self._rollback_handler.rollback(intent, intent.rollback_code, request.result_reference)
        except Exception:
            self._audit(request, policy_context, AuditStageV2.ROLLBACK_FINISHED, DispatchStatusV2.ROLLBACK_FAILED, "ROLLBACK_HANDLER_FAILED")
            return ActionDispatchResultV2(DispatchStatusV2.ROLLBACK_FAILED, "ROLLBACK_HANDLER_FAILED", intent.action_id)
        self._audit(request, policy_context, AuditStageV2.ROLLBACK_FINISHED, DispatchStatusV2.ROLLED_BACK, "ROLLBACK_COMPLETE", result)
        return ActionDispatchResultV2(DispatchStatusV2.ROLLED_BACK, "ROLLBACK_COMPLETE", intent.action_id, result_reference=result)

    def _deny(self, request: RollbackRequestV2, context: ActionPolicyContextV2, reason: str) -> ActionDispatchResultV2:
        self._audit(request, context, AuditStageV2.DECISION, DispatchStatusV2.DENIED, reason)
        return ActionDispatchResultV2(DispatchStatusV2.DENIED, reason, request.intent.action_id)
