from datetime import datetime, timedelta, timezone

import pytest

from marketcore.action.authorization_v2 import AuthorizationGrantV2, ScopeAuthorizationEngineV2
from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.action.dispatcher_v2 import (
    ActionDispatchErrorV2,
    AuditStageV2,
    DispatchStatusV2,
    GovernedActionDispatcherV2,
    RiskDecisionV2,
    RiskVerdictV2,
)
from marketcore.action.policy_v2 import ActionPolicyContextV2, ActionPolicyRuleV2, AutonomyModeV2, StaticActionPolicyEngineV2
from marketcore.presentation.render_tree.v2 import ActionKindV2


NOW = datetime(2026, 7, 15, 13, tzinfo=timezone.utc)


class Risk:
    def __init__(self, verdict: RiskVerdictV2 = RiskVerdictV2.ALLOW, *, fail: bool = False, calls: list[str] | None = None) -> None:
        self.verdict, self.fail, self.calls = verdict, fail, calls if calls is not None else []

    def evaluate(self, intent, guard_code, *, now):
        self.calls.append("risk")
        if self.fail:
            raise RuntimeError("risk offline")
        return RiskDecisionV2(self.verdict, "RISK_ALLOWED" if self.verdict is RiskVerdictV2.ALLOW else "RISK_LIMIT_DENIED", guard_code)


class Duplicates:
    def __init__(self, claimed: bool = True, *, calls: list[str] | None = None) -> None:
        self.claimed, self.calls = claimed, calls if calls is not None else []

    def claim(self, key, *, now):
        self.calls.append("duplicate")
        return self.claimed


class Audit:
    def __init__(self, *, fail: bool = False, calls: list[str] | None = None) -> None:
        self.events, self.fail, self.calls = [], fail, calls if calls is not None else []

    def append(self, event):
        self.calls.append(f"audit:{event.stage.value}")
        if self.fail:
            raise RuntimeError("audit offline")
        self.events.append(event)


class Handler:
    def __init__(self, *, fail: bool = False, calls: list[str] | None = None) -> None:
        self.count, self.fail, self.calls = 0, fail, calls if calls is not None else []

    def execute(self, intent):
        self.count += 1
        self.calls.append("handler")
        if self.fail:
            raise RuntimeError("handler failed")
        return "result.refresh.1"


def command(*, approval: bool = False) -> ActionIntentV2:
    return ActionIntentV2(
        action_id="research.refresh",
        action_kind=ActionKindV2.COMMAND,
        interaction_kind=InteractionKindV2.DOUBLE_CLICK,
        actor_kind=ActionActorKindV2.OPERATOR,
        actor_id="operator.test",
        command_code="RESEARCH.REFRESH",
        policy_class="RESEARCH_MAINTENANCE",
        authorization_scope="research:write",
        requires_approval=approval,
        reversible=not approval,
        rollback_code=None if approval else "RESEARCH.RESTORE_PREVIOUS_SNAPSHOT",
        idempotency_key="refresh-1",
    )


def navigation() -> ActionIntentV2:
    return ActionIntentV2(
        action_id="navigation.open.risk",
        action_kind=ActionKindV2.NAVIGATE,
        interaction_kind=InteractionKindV2.CLICK,
        actor_kind=ActionActorKindV2.OPERATOR,
        actor_id="operator.test",
        target_id="container.risk",
    )


def dispatcher(*, risk=None, duplicates=None, audit=None, handler=None, calls=None):
    calls = calls if calls is not None else []
    policy = StaticActionPolicyEngineV2({
        "RESEARCH_MAINTENANCE": ActionPolicyRuleV2(
            "RESEARCH_MAINTENANCE",
            frozenset({AutonomyModeV2.RECOMMEND}),
            frozenset({ActionActorKindV2.OPERATOR}),
            risk_guard_code="RISK.RESEARCH_RESOURCE_GUARD",
            valid_until=NOW + timedelta(hours=1),
        )
    })
    audit = audit or Audit(calls=calls)
    handler = handler or Handler(calls=calls)
    return (
        GovernedActionDispatcherV2(
            authorization=ScopeAuthorizationEngineV2(), policy=policy,
            risk=risk or Risk(calls=calls), duplicate_guard=duplicates or Duplicates(calls=calls),
            audit_trail=audit, command_handler=handler,
        ), audit, handler,
    )


def grant() -> AuthorizationGrantV2:
    return AuthorizationGrantV2("operator.test", frozenset({"research:write"}), NOW + timedelta(minutes=30))


def context(*, approval: bool = False) -> ActionPolicyContextV2:
    return ActionPolicyContextV2(AutonomyModeV2.RECOMMEND, NOW, approval_granted=approval)


def test_successful_command_is_risk_checked_deduplicated_and_audited_before_execution() -> None:
    calls = []
    d, audit, handler = dispatcher(calls=calls)
    result = d.dispatch(command(), grant=grant(), policy_context=context())
    assert result.status is DispatchStatusV2.EXECUTED
    assert calls == ["risk", "duplicate", "audit:EXECUTION_STARTED", "handler", "audit:EXECUTION_FINISHED"]
    assert [event.stage for event in audit.events] == [AuditStageV2.EXECUTION_STARTED, AuditStageV2.EXECUTION_FINISHED]
    assert handler.count == 1


def test_risk_denial_prevents_duplicate_claim_and_execution() -> None:
    risk = Risk(RiskVerdictV2.DENY)
    duplicates, audit, handler = Duplicates(), Audit(), Handler()
    d, _, _ = dispatcher(risk=risk, duplicates=duplicates, audit=audit, handler=handler)
    result = d.dispatch(command(), grant=grant(), policy_context=context())
    assert result.reason_code == "RISK_LIMIT_DENIED"
    assert duplicates.calls == [] and handler.count == 0
    assert audit.events[0].status is DispatchStatusV2.DENIED


def test_risk_boundary_failure_is_fail_closed() -> None:
    handler = Handler()
    d, audit, _ = dispatcher(risk=Risk(fail=True), handler=handler)
    result = d.dispatch(command(), grant=grant(), policy_context=context())
    assert result.reason_code == "RISK_BOUNDARY_UNAVAILABLE"
    assert handler.count == 0 and audit.events[0].reason_code == result.reason_code


def test_duplicate_action_is_not_executed_and_is_audited() -> None:
    handler = Handler()
    d, audit, _ = dispatcher(duplicates=Duplicates(False), handler=handler)
    result = d.dispatch(command(), grant=grant(), policy_context=context())
    assert result.status is DispatchStatusV2.DUPLICATE
    assert handler.count == 0 and audit.events[0].reason_code == "DUPLICATE_ACTION"


def test_audit_unavailable_prevents_execution() -> None:
    handler = Handler()
    d, _, _ = dispatcher(audit=Audit(fail=True), handler=handler)
    with pytest.raises(ActionDispatchErrorV2, match="ACTION_AUDIT_UNAVAILABLE"):
        d.dispatch(command(), grant=grant(), policy_context=context())
    assert handler.count == 0


def test_approval_required_does_not_reach_risk_or_handler() -> None:
    risk, handler = Risk(), Handler()
    d, audit, _ = dispatcher(risk=risk, handler=handler)
    result = d.dispatch(command(approval=True), grant=grant(), policy_context=context())
    assert result.status is DispatchStatusV2.APPROVAL_REQUIRED
    assert risk.calls == [] and handler.count == 0
    assert audit.events[0].approval_granted is False


def test_navigation_is_audited_without_risk_duplicate_or_command_handler() -> None:
    risk, duplicates, handler = Risk(), Duplicates(), Handler()
    d, audit, _ = dispatcher(risk=risk, duplicates=duplicates, handler=handler)
    result = d.dispatch(navigation(), grant=None, policy_context=context())
    assert result.status is DispatchStatusV2.NAVIGATED and result.target_id == "container.risk"
    assert risk.calls == [] and duplicates.calls == [] and handler.count == 0
    assert audit.events[0].reason_code == "NAVIGATION_ALLOWED"


def test_authorization_denial_is_audited_before_other_boundaries() -> None:
    risk, duplicates, handler = Risk(), Duplicates(), Handler()
    d, audit, _ = dispatcher(risk=risk, duplicates=duplicates, handler=handler)
    result = d.dispatch(command(), grant=None, policy_context=context())
    assert result.reason_code == "AUTHORIZATION_GRANT_MISSING"
    assert risk.calls == [] and duplicates.calls == [] and handler.count == 0
    assert audit.events[0].status is DispatchStatusV2.DENIED


def test_handler_failure_is_recorded_after_execution_started() -> None:
    handler = Handler(fail=True)
    d, audit, _ = dispatcher(handler=handler)
    result = d.dispatch(command(), grant=grant(), policy_context=context())
    assert result.status is DispatchStatusV2.FAILED
    assert [event.stage for event in audit.events] == [AuditStageV2.EXECUTION_STARTED, AuditStageV2.EXECUTION_FINISHED]
    assert audit.events[-1].reason_code == "COMMAND_HANDLER_FAILED"
