from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from marketcore.action.authorization_v2 import AuthorizationGrantV2
from marketcore.action.contract_v2 import ActionIntentV2, validate_action_intent_v2
from marketcore.action.policy_v2 import ActionPolicyContextV2, ActionPolicyVerdictV2
from marketcore.presentation.render_tree.v2 import ActionKindV2


class RiskVerdictV2(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class DispatchStatusV2(str, Enum):
    NAVIGATED = "NAVIGATED"
    EXECUTED = "EXECUTED"
    DENIED = "DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"


class AuditStageV2(str, Enum):
    DECISION = "DECISION"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_FINISHED = "EXECUTION_FINISHED"
    ROLLBACK_STARTED = "ROLLBACK_STARTED"
    ROLLBACK_FINISHED = "ROLLBACK_FINISHED"


class ActionDispatchErrorV2(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RiskDecisionV2:
    verdict: RiskVerdictV2
    reason_code: str
    guard_code: str

    @property
    def allowed(self) -> bool:
        return self.verdict is RiskVerdictV2.ALLOW


@dataclass(frozen=True, slots=True)
class ActionAuditEventV2:
    occurred_at: datetime
    stage: AuditStageV2
    action_id: str
    actor_id: str
    interaction_kind: str
    status: DispatchStatusV2
    reason_code: str
    target_id: str | None
    command_code: str | None
    policy_class: str | None
    risk_guard_code: str | None
    idempotency_key: str | None
    approval_granted: bool
    result_reference: str | None = None


@dataclass(frozen=True, slots=True)
class ActionDispatchResultV2:
    status: DispatchStatusV2
    reason_code: str
    action_id: str
    target_id: str | None = None
    result_reference: str | None = None

    @property
    def successful(self) -> bool:
        return self.status in {DispatchStatusV2.NAVIGATED, DispatchStatusV2.EXECUTED}


class AuthorizationBoundaryV2(Protocol):
    def authorize(self, intent: ActionIntentV2, grant: AuthorizationGrantV2 | None, *, now: datetime) -> Any: ...


class PolicyBoundaryV2(Protocol):
    def evaluate(self, intent: ActionIntentV2, context: ActionPolicyContextV2) -> Any: ...


class RiskBoundaryV2(Protocol):
    def evaluate(self, intent: ActionIntentV2, guard_code: str, *, now: datetime) -> RiskDecisionV2: ...


class DuplicateActionGuardV2(Protocol):
    def claim(self, idempotency_key: str, *, now: datetime) -> bool: ...


class ActionAuditTrailV2(Protocol):
    def append(self, event: ActionAuditEventV2) -> None: ...


class ActionCommandHandlerV2(Protocol):
    def execute(self, intent: ActionIntentV2) -> str: ...


class GovernedActionDispatcherV2:
    def __init__(
        self,
        *,
        authorization: AuthorizationBoundaryV2,
        policy: PolicyBoundaryV2,
        risk: RiskBoundaryV2,
        duplicate_guard: DuplicateActionGuardV2,
        audit_trail: ActionAuditTrailV2,
        command_handler: ActionCommandHandlerV2,
    ) -> None:
        self._authorization = authorization
        self._policy = policy
        self._risk = risk
        self._duplicate_guard = duplicate_guard
        self._audit_trail = audit_trail
        self._command_handler = command_handler

    def _audit(
        self,
        intent: ActionIntentV2,
        context: ActionPolicyContextV2,
        stage: AuditStageV2,
        status: DispatchStatusV2,
        reason_code: str,
        *,
        risk_guard_code: str | None = None,
        result_reference: str | None = None,
    ) -> None:
        try:
            self._audit_trail.append(
                ActionAuditEventV2(
                    occurred_at=context.now,
                    stage=stage,
                    action_id=intent.action_id,
                    actor_id=intent.actor_id,
                    interaction_kind=intent.interaction_kind.value,
                    status=status,
                    reason_code=reason_code,
                    target_id=intent.target_id,
                    command_code=intent.command_code,
                    policy_class=intent.policy_class,
                    risk_guard_code=risk_guard_code,
                    idempotency_key=intent.idempotency_key,
                    approval_granted=context.approval_granted,
                    result_reference=result_reference,
                )
            )
        except Exception as exc:
            raise ActionDispatchErrorV2("ACTION_AUDIT_UNAVAILABLE") from exc

    def dispatch(
        self,
        intent: ActionIntentV2,
        *,
        grant: AuthorizationGrantV2 | None,
        policy_context: ActionPolicyContextV2,
    ) -> ActionDispatchResultV2:
        validate_action_intent_v2(intent)
        authorization = self._authorization.authorize(intent, grant, now=policy_context.now)
        if not authorization.allowed:
            return self._deny(intent, policy_context, authorization.reason_code)

        policy = self._policy.evaluate(intent, policy_context)
        if policy.verdict is ActionPolicyVerdictV2.REQUIRE_APPROVAL:
            self._audit(intent, policy_context, AuditStageV2.DECISION, DispatchStatusV2.APPROVAL_REQUIRED, policy.reason_code, risk_guard_code=policy.risk_guard_code)
            return ActionDispatchResultV2(DispatchStatusV2.APPROVAL_REQUIRED, policy.reason_code, intent.action_id)
        if not policy.allowed:
            return self._deny(intent, policy_context, policy.reason_code, risk_guard_code=policy.risk_guard_code)

        if intent.action_kind is ActionKindV2.NAVIGATE:
            self._audit(intent, policy_context, AuditStageV2.DECISION, DispatchStatusV2.NAVIGATED, "NAVIGATION_ALLOWED")
            return ActionDispatchResultV2(DispatchStatusV2.NAVIGATED, "NAVIGATION_ALLOWED", intent.action_id, target_id=intent.target_id)

        risk_guard_code = policy.risk_guard_code
        if risk_guard_code is not None:
            try:
                risk = self._risk.evaluate(intent, risk_guard_code, now=policy_context.now)
            except Exception:
                return self._deny(intent, policy_context, "RISK_BOUNDARY_UNAVAILABLE", risk_guard_code=risk_guard_code)
            if not risk.allowed:
                return self._deny(intent, policy_context, risk.reason_code, risk_guard_code=risk_guard_code)

        try:
            claimed = self._duplicate_guard.claim(str(intent.idempotency_key), now=policy_context.now)
        except Exception:
            return self._deny(intent, policy_context, "DUPLICATE_GUARD_UNAVAILABLE", risk_guard_code=risk_guard_code)
        if not claimed:
            self._audit(intent, policy_context, AuditStageV2.DECISION, DispatchStatusV2.DUPLICATE, "DUPLICATE_ACTION", risk_guard_code=risk_guard_code)
            return ActionDispatchResultV2(DispatchStatusV2.DUPLICATE, "DUPLICATE_ACTION", intent.action_id)

        self._audit(intent, policy_context, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "ACTION_AUTHORIZED", risk_guard_code=risk_guard_code)
        try:
            result_reference = self._command_handler.execute(intent)
        except Exception:
            self._audit(intent, policy_context, AuditStageV2.EXECUTION_FINISHED, DispatchStatusV2.FAILED, "COMMAND_HANDLER_FAILED", risk_guard_code=risk_guard_code)
            return ActionDispatchResultV2(DispatchStatusV2.FAILED, "COMMAND_HANDLER_FAILED", intent.action_id)
        self._audit(intent, policy_context, AuditStageV2.EXECUTION_FINISHED, DispatchStatusV2.EXECUTED, "COMMAND_EXECUTED", risk_guard_code=risk_guard_code, result_reference=result_reference)
        return ActionDispatchResultV2(DispatchStatusV2.EXECUTED, "COMMAND_EXECUTED", intent.action_id, result_reference=result_reference)

    def _deny(
        self,
        intent: ActionIntentV2,
        context: ActionPolicyContextV2,
        reason_code: str,
        *,
        risk_guard_code: str | None = None,
    ) -> ActionDispatchResultV2:
        self._audit(intent, context, AuditStageV2.DECISION, DispatchStatusV2.DENIED, reason_code, risk_guard_code=risk_guard_code)
        return ActionDispatchResultV2(DispatchStatusV2.DENIED, reason_code, intent.action_id)
