from datetime import datetime, timedelta, timezone

from marketcore.action.authorization_v2 import AuthorizationGrantV2, ScopeAuthorizationEngineV2
from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.action.dispatcher_v2 import AuditStageV2, DispatchStatusV2
from marketcore.action.policy_v2 import ActionPolicyContextV2, ActionPolicyRuleV2, AutonomyModeV2, StaticActionPolicyEngineV2
from marketcore.action.rollback_v2 import GovernedRollbackCoordinatorV2, RollbackRequestV2
from marketcore.presentation.render_tree.v2 import ActionKindV2


NOW = datetime(2026, 7, 15, 14, tzinfo=timezone.utc)


class Duplicate:
    def __init__(self, claim=True): self.claim_value, self.keys = claim, []
    def claim(self, key, *, now): self.keys.append(key); return self.claim_value


class Audit:
    def __init__(self): self.events = []
    def append(self, event): self.events.append(event)


class Handler:
    def __init__(self, fail=False): self.calls, self.fail = [], fail
    def rollback(self, intent, rollback_code, result_reference):
        self.calls.append((rollback_code, result_reference))
        if self.fail: raise RuntimeError("rollback failed")
        return "rollback.result.1"


def intent() -> ActionIntentV2:
    return ActionIntentV2(
        action_id="research.refresh", action_kind=ActionKindV2.COMMAND,
        interaction_kind=InteractionKindV2.DOUBLE_CLICK, actor_kind=ActionActorKindV2.OPERATOR,
        actor_id="operator.test", command_code="RESEARCH.REFRESH",
        policy_class="RESEARCH_MAINTENANCE", authorization_scope="research:write",
        reversible=True, rollback_code="RESEARCH.RESTORE_PREVIOUS_SNAPSHOT",
        idempotency_key="refresh-rollback-1",
    )


def coordinator(*, rollback_allowed=True, duplicate=True, handler_fail=False):
    policy = StaticActionPolicyEngineV2({
        "RESEARCH_MAINTENANCE": ActionPolicyRuleV2(
            "RESEARCH_MAINTENANCE", frozenset({AutonomyModeV2.RECOMMEND}),
            frozenset({ActionActorKindV2.OPERATOR}), valid_until=NOW + timedelta(hours=1),
            rollback_allowed=rollback_allowed, rollback_requires_approval=True,
        )
    })
    audit, handler, duplicates = Audit(), Handler(handler_fail), Duplicate(duplicate)
    return GovernedRollbackCoordinatorV2(
        authorization=ScopeAuthorizationEngineV2(), policy=policy,
        duplicate_guard=duplicates, audit_trail=audit, rollback_handler=handler,
    ), audit, handler, duplicates


def grant(): return AuthorizationGrantV2("operator.test", frozenset({"research:write"}), NOW + timedelta(minutes=30))
def context(approval=False): return ActionPolicyContextV2(AutonomyModeV2.RECOMMEND, NOW, approval_granted=approval)
def request(): return RollbackRequestV2(intent(), "result.refresh.1")


def test_rollback_requires_separate_approval() -> None:
    c, audit, handler, _ = coordinator()
    result = c.rollback(request(), grant=grant(), policy_context=context())
    assert result.status is DispatchStatusV2.APPROVAL_REQUIRED
    assert handler.calls == [] and audit.events[0].reason_code == "ROLLBACK_APPROVAL_REQUIRED"


def test_policy_can_forbid_rollback() -> None:
    c, audit, handler, _ = coordinator(rollback_allowed=False)
    result = c.rollback(request(), grant=grant(), policy_context=context(True))
    assert result.reason_code == "ROLLBACK_POLICY_FORBIDDEN"
    assert handler.calls == [] and audit.events[0].status is DispatchStatusV2.DENIED


def test_successful_rollback_is_deduplicated_and_audited() -> None:
    c, audit, handler, duplicate = coordinator()
    result = c.rollback(request(), grant=grant(), policy_context=context(True))
    assert result.status is DispatchStatusV2.ROLLED_BACK
    assert duplicate.keys == ["rollback:refresh-rollback-1"]
    assert handler.calls == [("RESEARCH.RESTORE_PREVIOUS_SNAPSHOT", "result.refresh.1")]
    assert [event.stage for event in audit.events] == [AuditStageV2.ROLLBACK_STARTED, AuditStageV2.ROLLBACK_FINISHED]


def test_duplicate_rollback_is_not_executed() -> None:
    c, audit, handler, _ = coordinator(duplicate=False)
    result = c.rollback(request(), grant=grant(), policy_context=context(True))
    assert result.status is DispatchStatusV2.DUPLICATE
    assert handler.calls == [] and audit.events[0].reason_code == "ROLLBACK_DUPLICATE"


def test_rollback_failure_is_audited() -> None:
    c, audit, _, _ = coordinator(handler_fail=True)
    result = c.rollback(request(), grant=grant(), policy_context=context(True))
    assert result.status is DispatchStatusV2.ROLLBACK_FAILED
    assert audit.events[-1].reason_code == "ROLLBACK_HANDLER_FAILED"
