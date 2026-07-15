from datetime import datetime, timedelta, timezone

from marketcore.action.contract_v2 import ActionActorKindV2, ActionIntentV2, InteractionKindV2
from marketcore.action.dispatcher_v2 import RiskVerdictV2
from marketcore.action.postgres_risk_boundary_v2 import PostgresRiskBoundaryV2, RiskPermissionStateV2, evaluate_risk_permission_v2
from marketcore.presentation.render_tree.v2 import ActionKindV2


NOW = datetime(2026, 7, 15, 15, tzinfo=timezone.utc)


def intent() -> ActionIntentV2:
    return ActionIntentV2(
        action_id="research.refresh", action_kind=ActionKindV2.COMMAND,
        interaction_kind=InteractionKindV2.DOUBLE_CLICK, actor_kind=ActionActorKindV2.OPERATOR,
        actor_id="operator.test", command_code="RESEARCH.REFRESH",
        policy_class="RESEARCH_MAINTENANCE", authorization_scope="research:write",
        reversible=True, rollback_code="RESEARCH.RESTORE_PREVIOUS_SNAPSHOT", idempotency_key="risk-test-1",
    )


def state(**overrides) -> RiskPermissionStateV2:
    values = dict(runtime_allowed=True, execution_allowed=False, micro_live_allowed=False, refreshed_at=NOW - timedelta(seconds=30), maximum_age_seconds=900)
    values.update(overrides)
    return RiskPermissionStateV2(**values)


def test_research_guard_allows_current_snapshot_without_execution_permission() -> None:
    decision = evaluate_risk_permission_v2(state(), "RISK.RESEARCH_RESOURCE_GUARD", now=NOW)
    assert decision.verdict is RiskVerdictV2.ALLOW


def test_execution_guards_use_exact_permission() -> None:
    denied = evaluate_risk_permission_v2(state(), "RISK.EXECUTION_GUARD", now=NOW)
    allowed = evaluate_risk_permission_v2(state(execution_allowed=True), "RISK.EXECUTION_GUARD", now=NOW)
    assert denied.reason_code == "RISK_PERMISSION_DENIED"
    assert allowed.verdict is RiskVerdictV2.ALLOW


def test_stale_future_and_unknown_guards_fail_closed() -> None:
    stale = evaluate_risk_permission_v2(state(refreshed_at=NOW - timedelta(seconds=901)), "RISK.RESEARCH_RESOURCE_GUARD", now=NOW)
    future = evaluate_risk_permission_v2(state(refreshed_at=NOW + timedelta(seconds=1)), "RISK.RESEARCH_RESOURCE_GUARD", now=NOW)
    unknown = evaluate_risk_permission_v2(state(), "RISK.UNKNOWN", now=NOW)
    assert stale.reason_code == "RISK_PERMISSION_STALE"
    assert future.reason_code == "RISK_PERMISSION_STALE"
    assert unknown.reason_code == "RISK_GUARD_UNKNOWN"


def test_production_risk_snapshot_is_not_falsely_allowed() -> None:
    decision = PostgresRiskBoundaryV2().evaluate(intent(), "RISK.RESEARCH_RESOURCE_GUARD", now=datetime.now(timezone.utc))
    assert decision.verdict is RiskVerdictV2.DENY
    assert decision.reason_code in {"RISK_PERMISSION_STALE", "RISK_PERMISSION_UNAVAILABLE", "RISK_CONFIGURATION_UNAVAILABLE"}
